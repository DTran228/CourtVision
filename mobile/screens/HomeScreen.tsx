import { Button, ScrollView, StyleSheet, Text } from 'react-native';

// A prop is information or a function passed in by a parent component.
type HomeScreenProps = {
  onContinue: () => void;
};

export default function HomeScreen({ onContinue }: HomeScreenProps) {
  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Text style={styles.label}>BASKETBALL PRACTICE</Text>
      <Text style={styles.title}>CourtVision</Text>
      <Text style={styles.description}>
        Start with a short video from your practice session.
      </Text>
      <Button title="Get started" onPress={onContinue} color="#b45309" />
      <Text style={styles.note}>
        This first version lets you select a video and view its details.
        Shot analysis is coming later.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, justifyContent: 'center', padding: 24, gap: 20 },
  label: { color: '#b45309', fontSize: 13, fontWeight: '700', letterSpacing: 2 },
  title: { color: '#0f172a', fontSize: 38, fontWeight: '700' },
  description: { color: '#334155', fontSize: 19, lineHeight: 28 },
  note: { color: '#475569', fontSize: 15, lineHeight: 23 },
});
