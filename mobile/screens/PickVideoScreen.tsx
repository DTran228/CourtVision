import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Button, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Connection, Job, request, upload } from '../api';

type PickVideoScreenProps = {
  onBack: () => void;
  connection: Connection;
  onSession: (id: string) => void;
  initialJobId?: string;
};

export default function PickVideoScreen({ onBack, connection, onSession, initialJobId }: PickVideoScreenProps) {
  // null means no video has been selected yet.
  const [video, setVideo] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [isPicking, setIsPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [bytes, setBytes] = useState(0);
  const [job, setJob] = useState<Job | null>(null);
  const [jobId, setJobId] = useState(initialJobId ?? '');
  const [error, setError] = useState('');
  const [pollEpoch, setPollEpoch] = useState(0);
  const uploadedId = useRef('');
  const key = useRef(`phone-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const cancel = useRef<(() => void) | null>(null);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; cancel.current?.(); }; }, []);
  useEffect(() => {
    if (!jobId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    let delay = 1000;
    async function poll() {
      try {
        const value = await request<Job>(connection, `/jobs/${jobId}`);
        if (!active) return;
        setJob(value); setError('');
        if (value.status === 'succeeded' || value.status === 'failed') return;
        delay = Math.min(10000, delay*1.4);
      } catch (e) { if (!active) return; setError(String(e)); delay = Math.min(30000, delay*2); }
      if (active) timer = setTimeout(poll, delay);
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId, pollEpoch]);

  async function analyze() {
    if (!video || busy) return;
    if ((video.fileSize ?? 0) > 250*1024*1024 || (video.duration ?? 0) > 120000) {
      setError('Choose a clip at most 120 seconds and 250 MiB.'); return;
    }
    setBusy(true); setError('');
    try {
      if (!uploadedId.current) {
        const transfer = upload(connection, video.uri, video.mimeType ?? 'video/mp4', setBytes);
        cancel.current = transfer.cancel;
        uploadedId.current = (await transfer.promise).id;
      }
      const value = await request<Job>(connection, '/jobs', { method: 'POST', body: JSON.stringify({
        video_id: uploadedId.current, runner: 'local', settings: {}, idempotency_key: key.current,
      }) });
      if (alive.current) { setJob(value); setJobId(value.id); setPollEpoch(e => e+1); }
    } catch (e) { if (alive.current) setError(String(e)); }
    finally { cancel.current = null; if (alive.current) setBusy(false); }
  }
  async function retry() {
    setBusy(true); setError('');
    try { setJob(await request<Job>(connection, `/jobs/${jobId}/retry`, { method: 'POST' })); setPollEpoch(e => e+1); }
    catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  }

  async function pickVideo() {
    if (isPicking) return;
    setIsPicking(true);

    try {
      // iOS needs library access when returning the original video file.
      if (Platform.OS === 'ios') {
        const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!permission.granted) {
          Alert.alert(
            'Photo library access needed',
            'Allow photo library access for Expo Go in iPhone Settings, then try again.',
          );
          return;
        }
      }

      // await pauses this function while the phone's picker is open.
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['videos'],
        allowsMultipleSelection: false,
        allowsEditing: false,
      });

      // Canceling leaves the previous selection unchanged.
      if (result.canceled) return;

      const selectedVideo = result.assets[0];
      if (!selectedVideo || selectedVideo.type !== 'video') {
        Alert.alert('No video selected', 'Please choose a video from your library.');
        return;
      }
      setVideo(selectedVideo);
      uploadedId.current = ''; key.current = `phone-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setJobId(''); setJob(null); setBytes(0); setError('');
    } catch {
      Alert.alert('Could not open video', 'Please try again with a video saved on your phone.');
    } finally {
      // Re-enable the buttons after success, cancellation, or an error.
      setIsPicking(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Button title="Back to Home" onPress={onBack} disabled={isPicking || busy} />
      <Text style={styles.title}>Choose your video</Text>
      <Text style={styles.description}>
        Pick a short basketball clip from your photo library.
      </Text>

      <Button
        title={video ? 'Choose another video' : 'Choose video'}
        onPress={pickVideo}
        disabled={isPicking || busy || job?.status === 'running' || job?.status === 'queued'}
        color="#b45309"
      />
      {isPicking && <ActivityIndicator accessibilityLabel="Opening video" color="#b45309" />}
      {!!error && <Text accessibilityRole="alert" style={{ color: '#b91c1c' }}>{error}</Text>}
      {busy && <><ActivityIndicator /><Text>Sending request · {(bytes/1024/1024).toFixed(1)} MiB uploaded</Text><Button title="Cancel upload" onPress={() => cancel.current?.()} disabled={!cancel.current} /></>}
      {video && !job && <Button title="Upload and analyze on computer" onPress={analyze} disabled={busy || isPicking} />}
      {job && <View style={styles.card}>
        <Text>Job {job.id}</Text><Text>{job.status} · {job.stage} · attempt {job.attempt}</Text>
        {job.processed != null && job.total != null && <Text>{job.processed}/{job.total} frames</Text>}
        {job.error && <Text>{job.error.type}: {job.error.message}</Text>}
        {job.status === 'failed' && !job.dispatch_intent && <Button title="Retry failed analysis" onPress={retry} disabled={busy} />}
        {job.session_id && <Button title="Review results" onPress={() => onSession(job.session_id!)} />}
      </View>}

      {video && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Video selected</Text>
          <Text style={styles.detail}>Name: {video.fileName ?? 'Name unavailable'}</Text>
          <Text style={styles.detail}>
            Resolution: {video.width} × {video.height}
          </Text>
          <Text style={styles.detail}>
            {/* The picker reports duration in milliseconds. Divide by 1000 for seconds. */}
            Duration: {video.duration == null ? 'Unavailable' : `${(video.duration / 1000).toFixed(2)} seconds`}
          </Text>
          <Text style={styles.detail}>
            Size: {video.fileSize == null ? 'Unavailable' : `${(video.fileSize / 1024 / 1024).toFixed(2)} MiB`}
          </Text>
        </View>
      )}

      <Text style={styles.note}>
        Analysis starts only when you tap Upload. Use one visible hoop, a stationary camera,
        and CFR footage up to 120 seconds / 250 MiB / 1080p. Results are estimates to review.
        Submitted jobs remain available from Home after leaving this screen.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 24, gap: 20 },
  title: { color: '#0f172a', fontSize: 30, fontWeight: '700' },
  description: { color: '#334155', fontSize: 17, lineHeight: 25 },
  card: { backgroundColor: '#ffffff', borderColor: '#cbd5e1', borderWidth: 1, borderRadius: 12, padding: 20, gap: 12 },
  cardTitle: { color: '#166534', fontSize: 20, fontWeight: '600' },
  detail: { color: '#334155', fontSize: 16, lineHeight: 24 },
  note: { color: '#475569', fontSize: 15, lineHeight: 23 },
});
