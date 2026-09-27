import { useState } from 'react';
import { StyleSheet } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

import HomeScreen from './screens/HomeScreen';
import PickVideoScreen from './screens/PickVideoScreen';

export default function App() {
  // State is a value React remembers. Updating it redraws the screen.
  const [screen, setScreen] = useState<'home' | 'pick-video'>('home');

  return (
    <SafeAreaProvider>
      {/* Keep content clear of the iPhone notch and home indicator. */}
      <SafeAreaView style={styles.container}>
        <StatusBar style="dark" />
        {screen === 'home' ? (
          <HomeScreen onContinue={() => setScreen('pick-video')} />
        ) : (
          <PickVideoScreen onBack={() => setScreen('home')} />
        )}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
});
