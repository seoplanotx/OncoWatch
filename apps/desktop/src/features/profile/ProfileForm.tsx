import { useEffect, useMemo, useState } from 'react';
import type { Biomarker, PatientProfile, TherapyHistoryEntry } from '../../lib/types';

type ProfileFormProps = {
  initialValue?: PatientProfile | null;
  onSave: (profile: PatientProfile) => Promise<void>;
  submitLabel?: string;
};

function blankBiomarker(): Biomarker {
  return { name: '', variant: '', status: '', notes: '' };
}

function blankTherapy(): TherapyHistoryEntry {
  return { therapy_name: '', therapy_type: '', line_of_therapy: '', status: '', notes: '' };
}

const defaultProfile: PatientProfile = {
  profile_name: '',
  display_name: '',
  date_of_birth: '',
  cancer_type: '',
  subtype: '',
  stage_or_context: '',
  current_therapy_status: '',
  location_label: '',
  travel_radius_miles: 100,
  notes: '',
  would_consider: [],
  would_not_consider: [],
  is_active: true,
  biomarkers: [blankBiomarker()],
  therapy_history: [blankTherapy()]
};

export function ProfileForm({ initialValue, onSave, submitLabel = 'Save profile' }: ProfileFormProps) {
  const [form, setForm] = useState<PatientProfile>(initialValue || defaultProfile);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(initialValue || defaultProfile);
  }, [initialValue]);

  const considerText = useMemo(() => form.would_consider.join('\n'), [form.would_consider]);
  const avoidText = useMemo(() => form.would_not_consider.join('\n'), [form.would_not_consider]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await onSave({
        ...form,
        date_of_birth: form.date_of_birth || null,
        display_name: form.display_name || null,
        subtype: form.subtype || null,
        stage_or_context: form.stage_or_context || null,
        current_therapy_status: form.current_therapy_status || null,
        location_label: form.location_label || null,
        notes: form.notes || null,
        biomarkers: form.biomarkers.filter((item) => item.name.trim()),
        therapy_history: form.therapy_history.filter((item) => item.therapy_name.trim())
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="form-grid" onSubmit={handleSubmit}>
      <div className="field">
        <label>Profile name</label>
        <input value={form.profile_name} onChange={(e) => setForm({ ...form, profile_name: e.target.value })} required />
      </div>
      <div className="field">
        <label>Display name / initials</label>
        <input value={form.display_name || ''} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
      </div>
      <div className="field">
        <label>Date of birth</label>
        <input type="date" value={form.date_of_birth || ''} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} />
      </div>
      <div className="field">
        <label>Cancer type</label>
        <input value={form.cancer_type} onChange={(e) => setForm({ ...form, cancer_type: e.target.value })} required />
      </div>
      <div className="field">
        <label>Subtype</label>
        <input value={form.subtype || ''} onChange={(e) => setForm({ ...form, subtype: e.target.value })} />
      </div>
      <div className="field">
        <label>Stage / disease context</label>
        <input value={form.stage_or_context || ''} onChange={(e) => setForm({ ...form, stage_or_context: e.target.value })} />
      </div>
      <div className="field field-span-2">
        <label>Current therapy status</label>
        <textarea value={form.current_therapy_status || ''} onChange={(e) => setForm({ ...form, current_therapy_status: e.target.value })} rows={2} />
      </div>
      <div className="field">
        <label>Location</label>
        <input value={form.location_label || ''} onChange={(e) => setForm({ ...form, location_label: e.target.value })} />
      </div>
      <div className="field">
        <label>Travel radius (miles)</label>
        <input
          type="number"
          value={form.travel_radius_miles || 0}
          onChange={(e) => setForm({ ...form, travel_radius_miles: Number(e.target.value) })}
        />
      </div>

      <div className="section-divider field-span-2">Biomarkers / mutations</div>
      {form.biomarkers.map((item, index) => (
        <div key={`bio-${index}`} className="row-card">
          <div className="row-card-grid">
            <div className="field">
              <label>Name</label>
              <input
                value={item.name}
                onChange={(e) => {
                  const biomarkers = [...form.biomarkers];
                  biomarkers[index] = { ...item, name: e.target.value };
                  setForm({ ...form, biomarkers });
                }}
              />
            </div>
            <div className="field">
              <label>Variant</label>
              <input
                value={item.variant || ''}
                onChange={(e) => {
                  const biomarkers = [...form.biomarkers];
                  biomarkers[index] = { ...item, variant: e.target.value };
                  setForm({ ...form, biomarkers });
                }}
              />
            </div>
            <div className="field">
              <label>Status</label>
              <input
                value={item.status || ''}
                onChange={(e) => {
                  const biomarkers = [...form.biomarkers];
                  biomarkers[index] = { ...item, status: e.target.value };
                  setForm({ ...form, biomarkers });
                }}
              />
            </div>
          </div>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              const next = form.biomarkers.filter((_, idx) => idx !== index);
              setForm({ ...form, biomarkers: next.length ? next : [blankBiomarker()] });
            }}
          >
            Remove biomarker
          </button>
        </div>
      ))}
      <button type="button" className="secondary-button field-span-2" onClick={() => setForm({ ...form, biomarkers: [...form.biomarkers, blankBiomarker()] })}>
        Add biomarker
      </button>

      <div className="section-divider field-span-2">Therapy history</div>
      {form.therapy_history.map((item, index) => (
        <div key={`therapy-${index}`} className="row-card">
          <div className="row-card-grid">
            <div className="field">
              <label>Therapy</label>
              <input
                value={item.therapy_name}
                onChange={(e) => {
                  const therapy_history = [...form.therapy_history];
                  therapy_history[index] = { ...item, therapy_name: e.target.value };
                  setForm({ ...form, therapy_history });
                }}
              />
            </div>
            <div className="field">
              <label>Type</label>
              <input
                value={item.therapy_type || ''}
                onChange={(e) => {
                  const therapy_history = [...form.therapy_history];
                  therapy_history[index] = { ...item, therapy_type: e.target.value };
                  setForm({ ...form, therapy_history });
                }}
              />
            </div>
            <div className="field">
              <label>Status</label>
              <input
                value={item.status || ''}
                onChange={(e) => {
                  const therapy_history = [...form.therapy_history];
                  therapy_history[index] = { ...item, status: e.target.value };
                  setForm({ ...form, therapy_history });
                }}
              />
            </div>
          </div>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              const next = form.therapy_history.filter((_, idx) => idx !== index);
              setForm({ ...form, therapy_history: next.length ? next : [blankTherapy()] });
            }}
          >
            Remove therapy entry
          </button>
        </div>
      ))}
      <button type="button" className="secondary-button field-span-2" onClick={() => setForm({ ...form, therapy_history: [...form.therapy_history, blankTherapy()] })}>
        Add therapy
      </button>

      <div className="field field-span-2">
        <label>Would consider</label>
        <textarea
          rows={3}
          value={considerText}
          onChange={(e) =>
            setForm({
              ...form,
              would_consider: e.target.value
                .split('\n')
                .map((item) => item.trim())
                .filter(Boolean)
            })
          }
        />
      </div>
      <div className="field field-span-2">
        <label>Would not consider</label>
        <textarea
          rows={3}
          value={avoidText}
          onChange={(e) =>
            setForm({
              ...form,
              would_not_consider: e.target.value
                .split('\n')
                .map((item) => item.trim())
                .filter(Boolean)
            })
          }
        />
      </div>
      <div className="field field-span-2">
        <label>Notes</label>
        <textarea value={form.notes || ''} rows={4} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      </div>
      <div className="field-span-2">
        <button className="primary-button" disabled={saving} type="submit">
          {saving ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}
