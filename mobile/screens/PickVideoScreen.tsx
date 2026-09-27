import { useState } from 'react';
import { ActivityIndicator, Alert, Button, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

type PickVideoScreenProps = {
  onBack: () => void;
};

export default function PickVideoScreen({ onBack }: PickVideoScreenProps) {
  // null means no video has been selected yet.
  const [video, setVideo] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [isPicking, setIsPicking] = useState(false);

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
    } catch {
      Alert.alert('Could not open video', 'Please try again with a video saved on your phone.');
    } finally {
      // Re-enable the buttons after success, cancellation, or an error.
      setIsPicking(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Button title="Back to Home" onPress={onBack} disabled={isPicking} />
      <Text style={styles.title}>Choose your video</Text>
      <Text style={styles.description}>
        Pick a short basketball clip from your photo library.
      </Text>

      <Button
        title={video ? 'Choose another video' : 'Choose video'}
        onPress={pickVideo}
        disabled={isPicking}
        color="#b45309"
      />
      {isPicking && <ActivityIndicator accessibilityLabel="Opening video" color="#b45309" />}

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
        Your video stays on this phone. Nothing is uploaded or analyzed yet.
        Going back to Home clears this selection.
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
