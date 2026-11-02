import { useEffect, useState } from 'react';
import { Button, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Connection, Job, request, SessionRow } from '../api';

// A prop is information or a function passed in by a parent component.
type HomeScreenProps = {
  onContinue: () => void;
  connection: Connection;
  setConnection: (value: Connection) => void;
  onSession: (id: string) => void;
  onJob: (id: string) => void;
};

export default function HomeScreen({ onContinue, connection, setConnection, onSession, onJob }: HomeScreenProps) {
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function refresh() {
    setBusy(true); setError('');
    try {
      const [s, j] = await Promise.all([request<SessionRow[]>(connection, '/sessions'), request<Job[]>(connection, '/jobs')]);
      setSessions(s); setJobs(j);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }
  useEffect(() => { void refresh(); }, []);
  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Text style={styles.label}>BASKETBALL PRACTICE</Text>
      <Text style={styles.title}>CourtVision</Text>
      <Text style={styles.description}>
        Start with a short video from your practice session.
      </Text>
      <Button title="Get started" onPress={onContinue} color="#b45309" />
      <Text>Computer's LAN URL (phone localhost points to the phone)</Text>
      <TextInput accessibilityLabel="Backend URL" autoCapitalize="none" autoCorrect={false} value={connection.url} onChangeText={url => setConnection({ ...connection, url })} style={styles.input} />
      <TextInput accessibilityLabel="Backend access token" secureTextEntry autoCapitalize="none" placeholder="Access token if backend requires it" value={connection.token} onChangeText={token => setConnection({ ...connection, token })} style={styles.input} />
      <Button title={busy ? 'Loading…' : 'Connect / refresh history'} onPress={refresh} disabled={busy} />
      {!!error && <Text accessibilityRole="alert" style={{ color: '#b91c1c' }}>{error}</Text>}
      <Text style={styles.label}>RECENT JOBS</Text>
      {jobs.filter(j => j.status !== 'succeeded').map(job => <Button key={job.id} title={`${job.status} · ${job.id.slice(0, 8)}`} onPress={() => onJob(job.id)} />)}
      <Text style={styles.label}>SESSION HISTORY</Text>
      {sessions.map(s => <View key={s.id}>
        <Button title={`Review ${s.id.slice(0, 8)} · revision ${s.revision}`} onPress={() => onSession(s.id)} />
        <Text>{s.review_summary.makes}/{s.review_summary.candidates} reviewed estimates · {s.review_summary.unknown} unknown · FG% {s.review_summary.fg_percent == null ? 'pending review' : s.review_summary.fg_percent.toFixed(1)}</Text>
      </View>)}
      {sessions.filter(s => s.review_summary.fg_percent != null).length >= 2 && <Text>
        Recent completed sessions (newest first): {sessions.filter(s => s.review_summary.fg_percent != null).map(s => `${s.review_summary.fg_percent!.toFixed(1)}% (${s.review_summary.makes}/${s.review_summary.candidates})`).join(' → ')}
      </Text>}
      <Text style={styles.note}>
        Upload, analyze, then inspect the original clip and correct attempts.
        Incomplete sessions and unknown outcomes do not contribute a definitive FG%.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  input: { borderWidth: 1, borderColor: '#94a3b8', padding: 12, borderRadius: 8 },
  content: { flexGrow: 1, justifyContent: 'center', padding: 24, gap: 20 },
  label: { color: '#b45309', fontSize: 13, fontWeight: '700', letterSpacing: 2 },
  title: { color: '#0f172a', fontSize: 38, fontWeight: '700' },
  description: { color: '#334155', fontSize: 19, lineHeight: 28 },
  note: { color: '#475569', fontSize: 15, lineHeight: 23 },
});
