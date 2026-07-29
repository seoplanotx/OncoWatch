/**
 * The upcoming-appointment details (date + doctor/clinic), kept in localStorage
 * so both places that can make a prep sheet — the Reports flow and the
 * Clinician Summary page — produce the same PDF header.
 */

const APPOINTMENT_KEY = 'firstlight.appointmentPrep';

export type Appointment = { date: string; doctor: string };

export function readAppointment(): Appointment {
  try {
    const raw = window.localStorage.getItem(APPOINTMENT_KEY);
    if (!raw) return { date: '', doctor: '' };
    const parsed = JSON.parse(raw) as Partial<Appointment>;
    return {
      date: typeof parsed.date === 'string' ? parsed.date : '',
      doctor: typeof parsed.doctor === 'string' ? parsed.doctor : ''
    };
  } catch {
    return { date: '', doctor: '' };
  }
}

export function writeAppointment(appointment: Appointment): void {
  try {
    window.localStorage.setItem(APPOINTMENT_KEY, JSON.stringify(appointment));
  } catch {
    // best-effort
  }
}

/** The generate-request fields for a prep sheet; empty inputs are omitted. */
export function appointmentPayload(appointment: Appointment): {
  appointment_date?: string;
  appointment_clinician?: string;
} {
  const payload: { appointment_date?: string; appointment_clinician?: string } = {};
  if (appointment.date) payload.appointment_date = appointment.date;
  if (appointment.doctor.trim()) payload.appointment_clinician = appointment.doctor.trim();
  return payload;
}
