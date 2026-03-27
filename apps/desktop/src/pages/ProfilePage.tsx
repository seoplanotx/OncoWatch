import { useEffect, useState } from 'react';

import { Card } from '../components/Card';
import { ProfileForm } from '../features/profile/ProfileForm';
import { api } from '../lib/api';
import type { PatientProfile } from '../lib/types';

export function ProfilePage() {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  async function load() {
    setLoading(true);
    try {
      const current = await api.getActiveProfile();
      setProfile(current);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSave(payload: PatientProfile) {
    const saved = payload.id ? await api.updateProfile(payload.id, payload) : await api.createProfile(payload);
    setProfile(saved);
    setMessage('Profile saved locally.');
  }

  if (loading) return <div className="loading-block">Loading patient profile…</div>;

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Profile context</div>
          <h1>Patient Profile</h1>
          <p className="page-lede">This structured profile drives the local rules-first matching engine and shapes which findings are surfaced.</p>
        </div>
      </div>

      <Card title="Profile editor" description="Add only the facts you are confident in. Leaving uncertain fields blank is safer than guessing.">
        {message && <div className="callout">{message}</div>}
        <ProfileForm initialValue={profile} onSave={handleSave} submitLabel={profile ? 'Save profile' : 'Create profile'} />
      </Card>
    </div>
  );
}
