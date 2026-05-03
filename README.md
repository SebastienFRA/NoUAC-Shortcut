# NoUAC Shortcut

![Screenshot](https://github.com/SebastienFRA/NoUAC-Shortcut/blob/main/Images/NoUAC%20Shortcut.png?raw=true)

## 🇫🇷 Français

**NoUAC Shortcut** est un petit utilitaire Windows qui permet de lancer n'importe quel programme nécessitant des droits administrateur **sans que la fenêtre de confirmation UAC n'apparaisse**, tout en gardant l'UAC actif pour le reste du système.

### Fonctionnement

Le programme crée une **tâche planifiée Windows** configurée pour s'exécuter avec les droits élevés, puis génère un **raccourci `.lnk`** sur le bureau qui déclenche cette tâche en un double-clic. L'icône du raccourci est automatiquement récupérée depuis l'exécutable du programme ciblé.

### Utilisation

1. Lancer **NoUAC Shortcut** en tant qu'administrateur
2. Sélectionner l'exécutable du programme concerné
3. Définir le nom du raccourci et de la tâche planifiée
4. Cliquer sur **Créer la tâche et le raccourci**

Le raccourci apparaît alors sur le bureau et permet de lancer le programme sans aucune popup UAC.

### Remarques

- L'UAC reste entièrement actif pour tous les autres programmes
- Aucune dépendance externe requise (utilise uniquement des outils Windows natifs)
- Compatible avec la majorité des jeux et logiciels nécessitant des droits administrateur

---

## 🇬🇧 English

**NoUAC Shortcut** is a small Windows utility that lets you launch any program requiring administrator rights **without the UAC confirmation prompt appearing**, while keeping UAC active for the rest of the system.

### How it works

The program creates a **Windows scheduled task** configured to run with elevated privileges, then generates a **`.lnk` shortcut** on the desktop that triggers this task with a double-click. The shortcut icon is automatically retrieved from the target program's executable.

### Usage

1. Run **NoUAC Shortcut** as administrator
2. Select the executable of the target program
3. Set the shortcut name and scheduled task name
4. Click **Create task and shortcut**

The shortcut then appears on the desktop and allows you to launch the program without any UAC popup.

### Notes

- UAC remains fully active for all other programs
- No external dependencies required (uses only native Windows tools)
- Compatible with most games and software that require administrator rights
