# CourtVision mobile: Lesson 2

This is the mobile part of Milestone 1. It uses React Native, Expo SDK 57, and
TypeScript. The flow is **Home -> Choose video -> View video details**.

The app selects an existing video from the phone's photo library. Recording,
playback, uploads, and shot analysis are later work. The Python backend does not
need to run for this lesson.

## Run on your iPhone

Dependencies have already been installed on this computer.

1. Install **Expo Go** from the iPhone App Store and sign in to an Expo account.
2. Connect your computer and iPhone to the same Wi-Fi network.
3. Open PowerShell and enter the mobile folder:

   ```powershell
   cd C:\dev\CourtVision\mobile
   ```

4. Sign in to the same Expo account on the computer:

   ```powershell
   node node_modules/expo/bin/cli login --browser
   ```

   Finish the login in your own browser. Do not put your password in project files
   or send it in chat. This signs in to Expo; it does not deploy CourtVision.

5. Start the local development server:

   ```powershell
   node node_modules/expo/bin/cli start --go
   ```

6. Keep the terminal open. Scan its QR code with the iPhone Camera app and open
   the link in Expo Go. Allow local network access if iOS asks.
7. Tap **Get started**, then **Choose video**. Allow photo library access and
   select the same short clip you copied to the computer for OpenCV.

Expo Go loads our app inside its existing native app, so we do not need an App
Store release or an iOS build on this Windows computer for this lesson. The
development server sends the app's JavaScript to your phone. Saving a screen's
code normally refreshes it on the phone. Stop the server with Ctrl+C.

As of September 2026, Expo Go on iPhone supports SDK 57 and requires the same
account in the CLI and on the phone. See the
[official Expo announcement](https://expo.dev/changelog/expo-go-57-login).

### If the app does not open

- **Login error:** check that both devices use the same Expo account.
- **SDK mismatch:** check that Expo Go supports SDK 57. Update Expo Go if needed.
- **Connection timeout:** confirm the devices share Wi-Fi and Expo Go has local
  network permission. A guest or school network may block device-to-device
  connections. On your own trusted network, Windows may also ask you to allow
  Node.js through the firewall.
- **Photo access denied:** enable access for Expo Go in iPhone Settings, then try
  again. Limited photo access is supported; include the clip you want to select.
- **Video missing:** this picker reads the photo library, not the Files app.
  Save the clip to Photos first. For the first test, use a clip downloaded onto
  the phone rather than one available only in iCloud.

## Understand the files

| File | Purpose |
| --- | --- |
| `index.ts` | Registers `App` as the starting component. |
| `App.tsx` | Remembers which screen to show and protects content from the notch. |
| `screens/HomeScreen.tsx` | Shows the introduction and Get started button. |
| `screens/PickVideoScreen.tsx` | Opens the picker, handles its result, and displays video details. |
| `app.json` | Sets the app name, appearance, and image-picker native configuration. |
| `package.json` | Lists dependencies and development commands. |
| `package-lock.json` | Records exact installed dependency versions; keep this in Git. |
| `tsconfig.json` | Enables Expo's TypeScript defaults and strict type checking. |

The permission text in `app.json` applies when we build our own native app later.
Expo Go uses the permissions configured in its own app.

### Four concepts to learn first

1. **Component:** a function that returns a piece of the interface. `Text` and
   `Button` are React Native components; `HomeScreen` is one we wrote.
2. **Props:** values passed from a parent component to a child. `App` passes
   `onContinue` to Home so its button can change the screen.
3. **State:** data React remembers between renders. `setVideo(...)` updates state
   and causes React to display the selected video's details.
4. **Async/await:** the picker takes time. `await` waits for its result without
   blocking the phone's interface. `finally` re-enables buttons even after an error.

`.tsx` means TypeScript with JSX, the markup-like syntax used to describe the UI.
For example, `useState<ImagePicker.ImagePickerAsset | null>(null)` means the state
holds either a video asset returned by Expo or `null` (nothing selected yet).

## Follow the picker function

Read `pickVideo()` from top to bottom:

1. Mark the picker as busy so the buttons are disabled.
2. On iPhone, request photo library permission before selecting an original video.
3. Open the system picker with `mediaTypes: ['videos']`.
4. If the user cancels, keep the existing selection.
5. Otherwise, save the first selected video in state.
6. On failure, show an explanation. Always clear the busy state afterward.

The asset includes a local `uri` that could be used for playback or upload later.
It is a location on the phone, not a path Python can open on your computer.
We display duration in seconds (Expo reports milliseconds) and size in MiB
(bytes divided by 1024 twice). Missing metadata is shown as unavailable.

Selection is temporary: returning Home removes the picker screen, so its state
is cleared. Restarting the app also clears it. There is no saved session yet.
With only two screens, a state variable is sufficient for navigation; a navigation
library can be added when we need a screen history, deep links, or tabs.

## Checks

From the `mobile` folder:

```powershell
node node_modules/typescript/bin/tsc --noEmit
node node_modules/expo/bin/cli install --check
node node_modules/expo/bin/cli export --platform ios --output-dir dist --max-workers 2
```

The first checks TypeScript. The second checks dependency compatibility. The
third compiles a local iOS JavaScript bundle; it does not build an IPA, install
anything on the phone, or deploy the app. Generated `dist` files are ignored.

Type checking and bundling cannot verify iOS permission dialogs. Complete this
manual checklist on your iPhone before calling M1 done:

- [ ] Home opens and Get started opens the selection screen.
- [ ] Choose video opens the native picker and shows videos.
- [ ] Selecting a clip displays its details.
- [ ] Canceling before selection leaves no selected-video card.
- [ ] Canceling when replacing a video preserves the previous selection.
- [ ] Denying permission shows a message; allowing it later lets you retry.
- [ ] Returning Home and opening the picker screen clears the selection.
- [ ] The selected clip is the same footage that OpenCV reads on the computer.

### Dependencies and npm on this machine

Normally, `npm ci` installs from the lockfile, `npm start` starts Expo, and
`npm run typecheck` checks TypeScript. This machine's npm launcher previously
pointed to a missing file, so the instructions above call installed tools through
Node directly. No global npm settings were changed.

If dependencies need to be reinstalled, this PowerShell command uses the working
npm installation on this machine:

```powershell
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' ci
```

The initial npm audit reports 10 moderate entries stemming from the transitive
`uuid` dependency used by Expo's Xcode tooling. npm suggests a breaking downgrade
to Expo 46. We have not applied it or overridden Expo's dependency versions.
Recheck this when updating Expo; do not use `npm audit fix --force` blindly.

References: [Expo ImagePicker](https://docs.expo.dev/versions/latest/sdk/imagepicker/),
[creating an Expo project](https://docs.expo.dev/get-started/create-a-project/).
