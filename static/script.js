// Этот скрипт используется ТОЛЬКО на странице booking.html
// Он будет искать id 'step-1', 'details-form' и т.д.
// Глобальные переменные isUserLoggedIn и userRole берутся из base.html

document.addEventListener('DOMContentLoaded', () => {

    // Проверяем, на странице ли мы бронирования
    if (!document.getElementById('step-1')) {
        return; // Если нет, ничего не делаем
    }

    // --- СОСТОЯНИЕ (выбор пользователя) ---
    const state = {
        currentStep: 1,
        selectedDorm: { id: null, name: '' },
        bookingDetails: {
            startDate: '',
            endDate: '',
            fullName: '',
            studyGroup: '',
            gender: null,
            practiceStart: '',
            practiceEnd: ''
        },
        selectedRoom: {
            roomId: null,
            bedId: null,
            roomNumber: ''
        }
    };

    // --- ЭЛЕМЕНТЫ DOM ---
    const steps = document.querySelectorAll('.step');
    const dormCards = document.querySelectorAll('.dorm-card');
    const detailsForm = document.getElementById('details-form');
    const btnBackToStep1 = document.getElementById('btn-back-to-step-1');
    const btnBackToStep2 = document.getElementById('btn-back-to-step-2');
    const btnBook = document.getElementById('btn-book');
    const genderOptions = document.querySelectorAll('.gender-option');
    const roomsPlaceholder = document.getElementById('rooms-placeholder');
    const roomSelectionContainer = document.getElementById('room-selection-container');

    // Модальное окно "Нет мест"
    const noBedsModal = document.getElementById('no-beds-modal');
    const closeNoBedsModal = document.getElementById('close-no-beds-modal');
    const nextAvailableDateMessage = document.getElementById('next-available-date-message');

    // --- ФУНКЦИИ ---

    function showStep(stepNumber) {
        state.currentStep = stepNumber;
        steps.forEach((step) => {
            if (step.id === `step-${stepNumber}`) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
            }
        });
        window.scrollTo(0, 0);
    }

     function validateDates() {
        const startDateInput = document.getElementById('start-date');
        const endDateInput = document.getElementById('end-date');
        const dateError = document.getElementById('date-error');

        const start = new Date(startDateInput.value);
        const end = new Date(endDateInput.value);
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        if (!startDateInput.value || !endDateInput.value) {
            dateError.textContent = 'Пожалуйста, выберите обе даты.';
            dateError.classList.remove('hidden');
            return false;
        }
        if (start < today) {
            dateError.textContent = 'Дата начала не может быть раньше сегодня.';
            dateError.classList.remove('hidden');
            return false;
        }
        if (end < start) {
            dateError.textContent = 'Дата окончания не может быть раньше даты начала.';
            dateError.classList.remove('hidden');
            return false;
        }

        dateError.classList.add('hidden');
        return true;
     }

    /**
     * Запрос комнат с сервера
     */
    async function renderRoomGrid() {
        const { id: dorm_id } = state.selectedDorm;
        const { startDate: start_date, endDate: end_date, gender } = state.bookingDetails;

        roomsPlaceholder.textContent = 'Загрузка комнат...';
        roomsPlaceholder.style.display = 'block';
        roomSelectionContainer.innerHTML = ''; // Очищаем

        try {
            // Отправляем запрос в app.py
            const response = await fetch(`/api/get-rooms?dorm_id=${dorm_id}&start_date=${start_date}&end_date=${end_date}&gender=${gender}`);
            if (!response.ok) {
                throw new Error('Ошибка при загрузке комнат.');
            }
            const rooms = await response.json();

            if (rooms.error) {
                 roomsPlaceholder.textContent = `Ошибка: ${rooms.error}`;
                 return;
            }

            roomsPlaceholder.style.display = 'none';

            let totalAvailableBeds = 0;
            const roomsByCapacity = { 2: [], 3: [] };

            rooms.forEach(room => {
                let roomHTML = `<div class="room-card" data-room-id="${room.id}" data-room-number="${room.number}">
                                    <h4 class="font-semibold text-lg text-center">Комната ${room.number}</h4>
                                    <div class="bed-container">`;

                room.beds.forEach(bed => {
                    let bedClass = bed.status; // 'available', 'occupied', 'unavailable', 'repair', 'occupied_by_you'
                    let bedTitle = '';

                    if (bed.status === 'available') {
                        totalAvailableBeds++;
                        bedTitle = 'Свободно';
                    } else if (bed.status === 'occupied_by_you') {
                        bedClass = 'bed-occupied-you'; // Новый класс
                        bedTitle = `Занято вами: ${bed.occupant}`;
                    } else if (bed.status === 'occupied') {
                        bedTitle = 'Занято';
                    } else if (bed.status === 'unavailable') {
                        bedTitle = 'Недоступно (другой пол)';
                    } else if (bed.status === 'repair') {
                        bedClass = 'bed-repair';
                        bedTitle = 'На ремонте';
                    }

                    roomHTML += `<div class="bed ${bedClass}" data-bed-id="${bed.id}" title="${bedTitle}"></div>`;
                });

                roomHTML += `</div></div>`;

                if (room.capacity === 2) {
                    roomsByCapacity[2].push(roomHTML);
                } else {
                    roomsByCapacity[3].push(roomHTML);
                }
            });

            // Вставляем HTML в DOM
            let finalHTML = '';
            if (roomsByCapacity[3].length > 0) {
                finalHTML += `<div>
                                <h3 class="text-xl font-semibold mb-4 border-b-2 border-gray-200 pb-2">3-местные комнаты</h3>
                                <div class="room-grid">${roomsByCapacity[3].join('')}</div>
                              </div>`;
            }
            if (roomsByCapacity[2].length > 0) {
                finalHTML += `<div>
                                <h3 class="text-xl font-semibold mb-4 border-b-2 border-gray-200 pb-2">2-местные комнаты</h3>
                                <div class="room-grid">${roomsByCapacity[2].join('')}</div>
                              </div>`;
            }
            if (finalHTML === '') {
                 finalHTML = '<p class="text-center text-gray-500">Не найдено комнат для этого общежития.</p>';
            }
            roomSelectionContainer.innerHTML = finalHTML;

            addBedClickListeners();

            // Проверяем, есть ли места
            if (totalAvailableBeds === 0) {
                // TODO: Добавить логику поиска следующей свободной даты
                nextAvailableDateMessage.textContent = "Попробуйте изменить даты или выбрать другое общежитие.";
                noBedsModal.classList.remove('hidden');
            }

        } catch (error) {
            roomsPlaceholder.style.display = 'block';
            roomsPlaceholder.textContent = `Ошибка: ${error.message}`;
        }
    }

    function addBedClickListeners() {
        document.querySelectorAll('.bed.available').forEach(bed => {
            bed.addEventListener('click', () => {
                document.querySelectorAll('.bed').forEach(b => b.classList.remove('selected-bed'));
                document.querySelectorAll('.room-card').forEach(rc => rc.classList.remove('selected-room'));

                bed.classList.add('selected-bed');
                const roomCard = bed.closest('.room-card');
                roomCard.classList.add('selected-room');

                state.selectedRoom.roomId = roomCard.dataset.roomId;
                state.selectedRoom.roomNumber = roomCard.dataset.roomNumber;
                state.selectedRoom.bedId = bed.dataset.bedId;

                document.getElementById('room-error').classList.add('hidden');
            });
        });
    }

    // --- ОБРАБОТЧИКИ СОБЫТИЙ ---

    dormCards.forEach(card => {
        card.addEventListener('click', () => {
            state.selectedDorm.id = card.dataset.dormId;
            state.selectedDorm.name = card.dataset.dormName;
            document.getElementById('selected-dorm-title').textContent = `Вы выбрали: ${state.selectedDorm.name}`;
            showStep(2);
        });
    });

    genderOptions.forEach(option => {
        option.addEventListener('click', () => {
            genderOptions.forEach(opt => opt.classList.remove('selected'));
            option.classList.add('selected');
            state.bookingDetails.gender = option.dataset.gender;
            document.getElementById('gender-error').classList.add('hidden');
        });
    });

    detailsForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const isDatesValid = validateDates();
        const isGenderSelected = !!state.bookingDetails.gender;

        if (!isGenderSelected) {
            document.getElementById('gender-error').classList.remove('hidden');
            return;
        }

        if (isDatesValid) {
            state.bookingDetails.startDate = document.getElementById('start-date').value;
            state.bookingDetails.endDate = document.getElementById('end-date').value;
            state.bookingDetails.fullName = document.getElementById('full-name').value;
            state.bookingDetails.studyGroup = document.getElementById('study-group').value;
            state.bookingDetails.practiceStart = document.getElementById('practice-start').value;
            state.bookingDetails.practiceEnd = document.getElementById('practice-end').value;

            document.getElementById('booking-details-summary').textContent =
                `Даты: ${state.bookingDetails.startDate} по ${state.bookingDetails.endDate}`;
            document.getElementById('gender-specific-text').textContent =
                state.bookingDetails.gender === 'male' ? 'мужчин' : 'женщин';

            showStep(3);
            await renderRoomGrid();
        }
    });

    btnBackToStep1.addEventListener('click', () => showStep(1));
    btnBackToStep2.addEventListener('click', () => showStep(2));

    btnBook.addEventListener('click', async () => {
        if (!state.selectedRoom.roomId || !state.selectedRoom.bedId) {
            document.getElementById('room-error').classList.remove('hidden');
            return;
        }

        const bookingData = {
            ...state.bookingDetails,
            ...state.selectedRoom
        };

        try {
            const response = await fetch('/api/book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookingData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                document.getElementById('success-message').textContent =
                    `Место №${state.selectedRoom.bedId} в комнате ${state.selectedRoom.roomNumber} (${state.selectedDorm.name}) успешно забронировано.`;
                showStep(4);
            } else {
                throw new Error(result.message || 'Неизвестная ошибка сервера.');
            }

        } catch (error) {
            document.getElementById('room-error').textContent = `Ошибка бронирования: ${error.message}`;
            document.getElementById('room-error').classList.remove('hidden');
        }
    });

    if (closeNoBedsModal) {
        closeNoBedsModal.addEventListener('click', () => {
            noBedsModal.classList.add('hidden');
            showStep(2);
        });
    }

});

// Глобальные переменные для хранения данных формы
let formData = {
    dormId: null,
    startDate: null,
    endDate: null,
    fullName: null,
    group: null,
    gender: null,
    practiceStart: null,
    practiceEnd: null,
    selectedBedId: null
};

// Функция переключения шагов
function goToStep(stepNumber) {
    document.querySelectorAll('.step').forEach(el => el.classList.add('hidden'));
    document.getElementById(`step-${stepNumber}`).classList.remove('hidden');

    // Скролл вверх
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Шаг 1 -> Шаг 2: Выбор общежития
function selectDorm(id, name) {
    formData.dormId = id;
    document.getElementById('selected-dorm-id').value = id;
    document.getElementById('selected-dorm-title').innerText = name;
    goToStep(2);
}

// Выбор пола
function selectGender(gender) {
    formData.gender = gender;
    document.getElementById('selected-gender').value = gender;

    // Визуальное выделение
    document.querySelectorAll('.gender-option').forEach(el => el.classList.remove('selected'));
    document.getElementById(`gender-${gender}`).classList.add('selected');
}

// Шаг 2 -> Шаг 3: Форма заполнена, загружаем комнаты
document.getElementById('details-form').addEventListener('submit', function(e) {
    e.preventDefault();

    // Собираем данные
    formData.startDate = document.getElementById('start-date').value;
    formData.endDate = document.getElementById('end-date').value;
    formData.fullName = document.getElementById('full-name').value;
    formData.group = document.getElementById('study-group').value;
    formData.practiceStart = document.getElementById('practice-start').value;
    formData.practiceEnd = document.getElementById('practice-end').value;

    if (!formData.gender) {
        alert("Нажимая 'Ок', Вы подтверждаете корректность введенных данных и готовы продолжить выбор места!");
        return;
    }

    goToStep(3);
    loadRooms();
});

// Загрузка комнат (AJAX)
async function loadRooms() {
    const container = document.getElementById('room-selection-container');
    const placeholder = document.getElementById('rooms-placeholder');

    container.innerHTML = '';
    placeholder.classList.remove('hidden');

    try {
        // Запрос к серверу за свободными местами
        // Нам нужно создать этот API route в app.py, если его нет
        const query = new URLSearchParams({
            dorm_id: formData.dormId,
            start_date: formData.startDate,
            end_date: formData.endDate,
            gender: formData.gender
        });

        const response = await fetch(`/api/available-beds?${query.toString()}`);
        const data = await response.json();

        placeholder.classList.add('hidden');

        if (data.length === 0) {
            container.innerHTML = '<div class="text-center text-red-500 font-bold p-10">Нет свободных мест на эти даты.</div>';
            return;
        }

        // Рендерим комнаты
        let html = '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">';
        data.forEach(room => {
            html += `
                <div class="border rounded-lg p-4 bg-white shadow">
                    <h3 class="font-bold mb-2">Комната ${room.number}</h3>
                    <div class="flex flex-wrap gap-2">
            `;

            room.beds.forEach(bed => {
                html += `
                    <div onclick="selectBed(${bed.id}, this)"
                         class="bed-available p-2 rounded text-center w-10 h-10 flex items-center justify-center cursor-pointer transition">
                         ${bed.id}
                    </div>
                `;
            });

            html += `</div></div>`;
        });
        html += '</div>';

        container.innerHTML = html;

    } catch (error) {
        console.error(error);
        placeholder.innerText = "Ошибка загрузки данных.";
    }
}

// Выбор кровати
function selectBed(bedId, element) {
    // Снимаем выделение со всех
    document.querySelectorAll('.bed-available').forEach(el => el.classList.remove('selected'));

    // Выделяем текущую
    element.classList.add('selected');
    formData.selectedBedId = bedId;

    // Активируем кнопку бронирования
    const btn = document.getElementById('btn-book');
    btn.disabled = false;
    btn.classList.remove('bg-gray-400', 'cursor-not-allowed');
    btn.classList.add('bg-rzd-red', 'hover:bg-red-800');
}

// Финальное бронирование (Шаг 3 -> Шаг 4)
document.getElementById('btn-book').addEventListener('click', async function() {
    if (!formData.selectedBedId) return;

    try {
        const response = await fetch('/book_room', { // Используем существующий роут
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, // Flask Form ожидает form-data
            body: new URLSearchParams({
                'dorm_id': formData.dormId,
                'room_id': 'auto', // Логика сервера сама найдет по bed_id, или нужно адаптировать
                'bed_id': formData.selectedBedId, // ВАЖНО: передать ID кровати
                'start_date': formData.startDate,
                'end_date': formData.endDate,
                'full_name': formData.fullName,
                'group': formData.group,
                'practice_start': formData.practiceStart,
                'practice_end': formData.practiceEnd
                // 'gender' обычно берется из свойства комнаты, но можно передать
            })
        });

        if (response.ok) {
            goToStep(4);
        } else {
            alert("Ошибка бронирования. Возможно, место уже занято.");
        }
    } catch (e) {
        alert("Ошибка сети");
    }
});