import { useEffect, useState } from 'react';
import { ActivityIndicator, Button, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';

import { auth, base, Connection, Outcome, request, ReviewEvent, Session } from '../api';

export default function ReviewScreen({ connection, id, onBack }: { connection: Connection; id: string; onBack: () => void }) {
  const [session, setSession] = useState<Session | null>(null);
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [timeEdits, setTimeEdits] = useState<Record<string, string>>({});
  const [complete, setComplete] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [newTime, setNewTime] = useState('');
  const [mediaError, setMediaError] = useState('');
  const player = useVideoPlayer(null);

  function accept(value: Session) {
    setSession(value); setEvents(value.review.events); setComplete(value.review.complete); setDirty(false);
    setTimeEdits(Object.fromEntries(value.review.events.map(e => [e.id, String(e.contact_seconds)])));
  }
  async function load() {
    setBusy(true); setError('');
    try { accept(await request<Session>(connection, `/sessions/${id}`)); }
    catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    void load();
    let alive = true;
    try {
      player.replaceAsync({ uri: `${base(connection)}/sessions/${id}/media`, headers: auth(connection) })
        .catch(e => { if (alive) setMediaError(String(e)); });
    } catch (e) { setMediaError(String(e)); }
    const subscription = player.addListener('statusChange', event => {
      if (event.status === 'error') setMediaError(event.error?.message ?? 'Video playback failed');
    });
    return () => { alive = false; subscription.remove(); };
  }, [id]);

  function change(id: string, outcome: Outcome) {
    setEvents(events.map(e => e.id === id ? { ...e, outcome } : e)); setDirty(true);
  }
  function add() {
    const t = newTime.trim() ? Number(newTime) : player.currentTime;
    if (!Number.isFinite(t) || t < 0 || !session || t > session.automatic.timebase.duration_seconds) {
      setError('Enter a timestamp within this clip.'); return;
    }
    setEvents([...events, { id: `manual-${Date.now()}-${Math.random().toString(36).slice(2)}`, contact_seconds: t, outcome: 'unknown' }]);
    setNewTime(''); setDirty(true);
  }
  async function save() {
    if (!session) return;
    if (events.some(e => {
      const text = timeEdits[e.id] ?? String(e.contact_seconds);
      return !text.trim() || !Number.isFinite(Number(text)) || Number(text) < 0 || Number(text) > session.automatic.timebase.duration_seconds;
    })) { setError('Each timestamp must be a number within the clip.'); return; }
    setBusy(true); setError('');
    try {
      accept(await request<Session>(connection, `/sessions/${id}/review`, {
        method: 'PATCH', body: JSON.stringify({ expected_revision: session.revision, events, complete }),
      }));
    } catch (e) { setError(`${String(e)}. A 409 means another review was saved. Reload to see it before editing again.`); }
    finally { setBusy(false); }
  }
  const unknown = events.filter(e => e.outcome === 'unknown').length;
  const makes = events.filter(e => e.outcome === 'made').length;

  return <ScrollView contentContainerStyle={styles.content}>
    <Button title="Back to history" onPress={onBack} disabled={busy || dirty} />
    {dirty && <Text>Unsaved edits. Save, or reload to discard before leaving.</Text>}
    <Text style={styles.title}>Review practice</Text>
    <Text>Automatic estimates can miss attempts. Watch the full clip before confirming completeness.</Text>
    <VideoView player={player} style={styles.video} nativeControls fullscreenOptions={{ enable: true }} />
    {!!mediaError && <Text style={styles.error}>{mediaError}</Text>}
    {!!error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
    {busy && <ActivityIndicator />}
    {session && <>
      <Text>Automatic: {session.automatic.summary.makes} made / {session.automatic.summary.candidates} candidates, {session.automatic.summary.unknown} unknown</Text>
      <Text>Review: {makes} made / {events.length} attempts, {unknown} unknown</Text>
      <Text>FG%: {complete && events.length > 0 && unknown === 0 ? `${(100*makes/events.length).toFixed(1)}%` : 'Finish review and resolve unknowns'}</Text>
      {[...events].sort((a, b) => a.contact_seconds-b.contact_seconds).map(event => <View key={event.id} style={styles.card}>
        <Button title={`Watch ${event.contact_seconds.toFixed(2)} s · ${event.outcome}`} onPress={() => { player.currentTime = Math.max(0, event.contact_seconds-1); player.play(); }} />
        <Text>{session.automatic.events.find(e => e.id === event.id)?.reason ?? 'Manually added attempt'}</Text>
        <TextInput accessibilityLabel={`Timestamp for ${event.id}`} keyboardType="decimal-pad" value={timeEdits[event.id] ?? String(event.contact_seconds)}
          onChangeText={text => {
            setTimeEdits({ ...timeEdits, [event.id]: text }); setDirty(true);
            const t = Number(text);
            if (text.trim() && Number.isFinite(t)) setEvents(events.map(e => e.id === event.id ? { ...e, contact_seconds: t } : e));
          }} />
        <View style={styles.row}>{(['made', 'missed', 'unknown'] as Outcome[]).map(outcome => <Button key={outcome} title={outcome} onPress={() => change(event.id, outcome)} />)}</View>
        <Button title="Remove false positive" onPress={() => { setEvents(events.filter(e => e.id !== event.id)); setDirty(true); }} />
      </View>)}
      <TextInput style={styles.input} accessibilityLabel="New attempt timestamp" placeholder="Seconds (blank = player position)" keyboardType="decimal-pad" value={newTime} onChangeText={setNewTime} />
      <Button title="Add missed attempt" onPress={add} />
      <View style={styles.row}><Switch value={complete} onValueChange={v => { setComplete(v); setDirty(true); }} /><Text>All attempts reviewed</Text></View>
      <Button title={`Save review (revision ${session.revision})`} onPress={save} disabled={busy} />
      <Text>{dirty ? 'Unsaved changes' : 'Review saved / loaded'}</Text>
    </>}
    <Button title="Reload saved review (discard edits)" onPress={load} disabled={busy} />
  </ScrollView>;
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 16 }, title: { fontSize: 28, fontWeight: '700' }, video: { height: 240, width: '100%' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  card: { padding: 14, gap: 8, backgroundColor: '#fff', borderRadius: 10 },
  error: { color: '#b91c1c' }, input: { borderWidth: 1, borderColor: '#94a3b8', padding: 10 },
});
