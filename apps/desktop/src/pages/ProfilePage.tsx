import { useEffect, useState } from 'react';

import { Card } from '../components/Card';
import { PageErrorState } from '../components/PageErrorState';
import { ProfileForm } from '../features/profile/ProfileForm';
import { api } from '../lib/api';
import { getErrorMessage } from '../lib/errors';
import type { PatientProfile } from '../lib/types';

export function ProfilePage() {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  async function load() {
    setLoading(true);
    setErrorMessage('');
    try {
      const current = await api.getActiveProfile();
      setProfile(current);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not load the active profile.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleSave(payload: PatientProfile) {
    setMessage('');
    setErrorMessage('');
    try {
      const saved = payload.id ? await api.updateProfile(payload.id, payload) : await api.createProfile(payload);
      setProfile(saved);
      setMessage('Profile saved locally.');
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Could not save the patient profile.'));
    }
  }

  if (loading) return <div className="loading-block">Loading patient profile...</div>;
  if (errorMessage && !profile) {
    return <PageErrorState title="Profile unavailable" message={errorMessage} onRetry={load} />;
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <div className="eyebrow">Profile context</div>
          <h1>Patient Profile</h1>
          <p className="page-lede">
            This structured profile drives the local rules-first matching engine and shapes which findings are surfaced.
          </p>
        </div>
      </div>

      <Card title="Profile editor" description="Add only the facts you are confident in. Leaving uncertain fields blank is safer than guessing.">
        {message && <div className="callout">{message}</div>}
        {errorMessage && <div className="callout callout-danger">{errorMessage}</div>}
        <ProfileForm initialValue={profile} onSave={handleSave} submitLabel={profile ? 'Save profile' : 'Create profile'} />
      </Card>
    </div>
  );
}
