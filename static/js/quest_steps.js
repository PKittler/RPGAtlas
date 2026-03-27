(function () {
    'use strict';

    const list = document.getElementById('steps-list');
    if (!list) return;

    const reorderUrl = list.dataset.reorderUrl;
    let dragSrc = null;

    function getItems() {
        return Array.from(list.querySelectorAll('.step-item'));
    }

    function updateOrderNumbers() {
        getItems().forEach(function (item, index) {
            const numEl = item.querySelector('span.font-mono');
            if (numEl) numEl.textContent = index + 1;
        });
    }

    function sendReorder() {
        const order = getItems().map(function (item) {
            return parseInt(item.dataset.stepPk, 10);
        });

        fetch(reorderUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '',
            },
            body: JSON.stringify({ order: order }),
        });
    }

    getItems().forEach(function (item) {
        item.setAttribute('draggable', 'true');

        item.addEventListener('dragstart', function (e) {
            dragSrc = item;
            item.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });

        item.addEventListener('dragend', function () {
            item.classList.remove('dragging');
            getItems().forEach(function (i) { i.classList.remove('drag-over'); });
            dragSrc = null;
        });

        item.addEventListener('dragover', function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            if (item !== dragSrc) {
                getItems().forEach(function (i) { i.classList.remove('drag-over'); });
                item.classList.add('drag-over');
            }
        });

        item.addEventListener('dragleave', function () {
            item.classList.remove('drag-over');
        });

        item.addEventListener('drop', function (e) {
            e.preventDefault();
            if (!dragSrc || dragSrc === item) return;

            item.classList.remove('drag-over');

            // Einfügeposition bestimmen
            const items = getItems();
            const srcIndex = items.indexOf(dragSrc);
            const dstIndex = items.indexOf(item);

            if (srcIndex < dstIndex) {
                list.insertBefore(dragSrc, item.nextSibling);
            } else {
                list.insertBefore(dragSrc, item);
            }

            updateOrderNumbers();
            sendReorder();
        });
    });
}());
