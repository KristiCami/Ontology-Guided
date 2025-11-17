<?php
declare(strict_types=1);

// Determine the day context either from the request or default to today.
$daySource = $_GET['day'] ?? $_POST['day'] ?? date('Y-m-d');
try {
    $dayDate = new DateTime($daySource);
} catch (Exception $exception) {
    $dayDate = new DateTime();
}

$daySlug = $dayDate->format('Y-m-d');
$dayLabel = $dayDate->format('l, d/m/Y');

// Resolve the booking timetable markup using available helpers.
$bookingTimetableMarkup = '';
if (function_exists('booking_timetable')) {
    $bookingTimetableMarkup = (string) booking_timetable($daySlug);
} elseif (function_exists('do_shortcode')) {
    $attribute = function_exists('esc_attr')
        ? esc_attr($daySlug)
        : htmlspecialchars($daySlug, ENT_QUOTES, 'UTF-8');
    $bookingTimetableMarkup = (string) do_shortcode(sprintf('[booking_timetable day="%s"]', $attribute));
} else {
    $bookingTimetableMarkup = sprintf(
        '<p class="booking-timetable__empty">%s</p>',
        htmlspecialchars(
            sprintf('Δεν υπάρχει διαθέσιμο booking_timetable για την %s.', $dayLabel),
            ENT_QUOTES,
            'UTF-8'
        )
    );
}
?>

<style>
.booking-timetable__button {
    background-color: #1a73e8;
    border: none;
    border-radius: 6px;
    color: #fff;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 600;
    padding: 0.65rem 1.5rem;
    transition: background-color 0.2s ease-in-out;
}

.booking-timetable__button:hover,
.booking-timetable__button:focus {
    background-color: #155fc0;
    outline: none;
}

.booking-timetable__modal {
    align-items: center;
    backdrop-filter: blur(1px);
    background-color: rgba(0, 0, 0, 0.45);
    display: none;
    height: 100vh;
    justify-content: center;
    left: 0;
    padding: 1rem;
    position: fixed;
    top: 0;
    width: 100vw;
    z-index: 9999;
}

.booking-timetable__modal.is-visible {
    display: flex;
}

.booking-timetable__dialog {
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    max-height: 90vh;
    max-width: 800px;
    overflow: hidden;
    width: 100%;
}

.booking-timetable__header {
    align-items: center;
    border-bottom: 1px solid #e3e8ef;
    display: flex;
    justify-content: space-between;
    padding: 1rem 1.25rem;
}

.booking-timetable__title {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
}

.booking-timetable__close {
    background: transparent;
    border: none;
    color: #64748b;
    cursor: pointer;
    font-size: 1.25rem;
    line-height: 1;
    padding: 0.25rem;
}

.booking-timetable__content {
    max-height: calc(90vh - 70px);
    overflow-y: auto;
    padding: 1rem 1.25rem;
}

.booking-timetable__empty {
    color: #64748b;
    font-size: 0.95rem;
    margin: 0;
}
</style>

<button
    id="bookingTimetableTrigger"
    class="booking-timetable__button"
    type="button"
    data-day="<?php echo htmlspecialchars($daySlug, ENT_QUOTES, 'UTF-8'); ?>"
>
    Προβολή προγράμματος κρατήσεων
</button>

<div
    id="bookingTimetableModal"
    class="booking-timetable__modal"
    role="dialog"
    aria-modal="true"
    aria-hidden="true"
>
    <div class="booking-timetable__dialog">
        <div class="booking-timetable__header">
            <p class="booking-timetable__title">
                Πρόγραμμα κρατήσεων για <?php echo htmlspecialchars($dayLabel, ENT_QUOTES, 'UTF-8'); ?>
            </p>
            <button class="booking-timetable__close" type="button" data-close-modal aria-label="Κλείσιμο">&times;</button>
        </div>
        <div class="booking-timetable__content">
            <?php echo $bookingTimetableMarkup; ?>
        </div>
    </div>
</div>

<script>
(function () {
    const trigger = document.getElementById('bookingTimetableTrigger');
    const modal = document.getElementById('bookingTimetableModal');

    if (!trigger || !modal) {
        return;
    }

    const toggleModal = (show) => {
        modal.setAttribute('aria-hidden', show ? 'false' : 'true');
        modal.classList.toggle('is-visible', show);
        if (!show) {
            trigger.focus();
        }
    };

    trigger.addEventListener('click', () => toggleModal(true));

    modal.addEventListener('click', (event) => {
        if (event.target === modal || event.target.dataset.closeModal !== undefined) {
            toggleModal(false);
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && modal.classList.contains('is-visible')) {
            toggleModal(false);
        }
    });
})();
</script>
