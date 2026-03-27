import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone


class SessionConsumer(AsyncWebsocketConsumer):

    # ── Verbindungs-Lifecycle ────────────────────────────────────────────

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f'session_{self.session_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        participant_info = await self.get_participant_info()
        if not participant_info:
            await self.close()
            return

        self.is_gamemaster = participant_info['role'] == 'gamemaster'
        self.character_id = participant_info['character_id']

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ── Eingehende Nachrichten ───────────────────────────────────────────

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, ValueError):
            return

        msg_type = data.get('type')

        if msg_type == 'move_figure':
            await self.handle_move_figure(data)
        elif msg_type == 'toggle_path':
            # Rein clientseitig, kein DB-Zugriff nötig
            await self.send(text_data=json.dumps({'type': 'toggle_path_ack'}))

    async def handle_move_figure(self, data):
        if not self.is_gamemaster:
            return

        character_id = data.get('character_id')
        x_raw = data.get('x_pos')
        y_raw = data.get('y_pos')
        gate_id = data.get('gate_id')

        if character_id is None or x_raw is None or y_raw is None:
            return

        x_pos = max(0.0, min(1.0, float(x_raw)))
        y_pos = max(0.0, min(1.0, float(y_raw)))

        if gate_id:
            result = await self.process_gate_transition(character_id, int(gate_id))
            if result:
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'figure_joined_map',
                    'character_id': character_id,
                    'old_map_id': result['old_map_id'],
                    'new_map_id': result['new_map_id'],
                    'x_pos': result['x_pos'],
                    'y_pos': result['y_pos'],
                })
        else:
            map_id = await self.save_character_position(character_id, x_pos, y_pos)
            if map_id:
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'figure_moved',
                    'character_id': character_id,
                    'map_id': map_id,
                    'x_pos': x_pos,
                    'y_pos': y_pos,
                })

    # ── Ausgehende Event-Handler (group_send → send) ─────────────────────

    async def figure_moved(self, event):
        await self.send(text_data=json.dumps({
            'type': 'figure_moved',
            'character_id': event['character_id'],
            'map_id': event['map_id'],
            'x_pos': event['x_pos'],
            'y_pos': event['y_pos'],
        }))

    async def figure_eliminated(self, event):
        await self.send(text_data=json.dumps({
            'type': 'figure_eliminated',
            'character_id': event['character_id'],
        }))

    async def session_ended(self, event):
        await self.send(text_data=json.dumps({'type': 'session_ended'}))

    async def figure_joined_map(self, event):
        await self.send(text_data=json.dumps({
            'type': 'figure_joined_map',
            'character_id': event['character_id'],
            'old_map_id': event['old_map_id'],
            'new_map_id': event['new_map_id'],
            'x_pos': event['x_pos'],
            'y_pos': event['y_pos'],
        }))

    # ── DB-Hilfsfunktionen ───────────────────────────────────────────────

    @database_sync_to_async
    def get_participant_info(self):
        from .models import SessionParticipant
        try:
            p = SessionParticipant.objects.select_related('character').get(
                session_id=self.session_id,
                user=self.user,
                is_removed=False,
                is_confirmed=True,
            )
            return {'role': p.role, 'character_id': p.character_id}
        except SessionParticipant.DoesNotExist:
            return None

    @database_sync_to_async
    def save_character_position(self, character_id, x_pos, y_pos):
        from .models import CharacterPosition, GameSession
        from characters.models import Character
        try:
            session = GameSession.objects.select_related('active_map').get(
                pk=self.session_id, status='running',
            )
            if not session.active_map:
                return None
            character = Character.objects.get(pk=character_id, current_session_id=self.session_id)
            CharacterPosition.objects.create(
                character=character,
                session=session,
                map=session.active_map,
                x_pos=x_pos,
                y_pos=y_pos,
            )
            GameSession.objects.filter(pk=self.session_id).update(last_activity=timezone.now())
            return session.active_map_id
        except Exception:
            return None

    @database_sync_to_async
    def process_gate_transition(self, character_id, gate_id):
        from .models import CharacterPosition, GameSession
        from characters.models import Character
        from maps.models import Gate
        try:
            session = GameSession.objects.select_related('active_map').get(
                pk=self.session_id, status='running',
            )
            character = Character.objects.get(pk=character_id, current_session_id=self.session_id)
            gate = Gate.objects.select_related('target_map').get(pk=gate_id)
            if not gate.target_map:
                return None

            old_map_id = session.active_map_id
            target_map = gate.target_map

            CharacterPosition.objects.create(
                character=character,
                session=session,
                map=target_map,
                x_pos=target_map.center_x,
                y_pos=target_map.center_y,
            )

            session.active_map = target_map
            session.save(update_fields=['active_map', 'last_activity'])

            return {
                'old_map_id': old_map_id,
                'new_map_id': target_map.pk,
                'x_pos': target_map.center_x,
                'y_pos': target_map.center_y,
            }
        except Exception:
            return None
