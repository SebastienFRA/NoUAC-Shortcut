import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import sys
import ctypes
import winreg
import xml.etree.ElementTree as ET
from pathlib import Path
import re


# ─── Vérification des droits admin ───────────────────────────────────────────

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """Relance le script avec élévation admin."""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{__file__}"', None, 1
    )
    sys.exit()


# ─── Logique principale ───────────────────────────────────────────────────────

def sanitize_task_name(path: str) -> str:
    """Génère un nom de tâche propre depuis le chemin de l'exe."""
    name = Path(path).stem
    name = re.sub(r'[^\w\-]', '_', name)
    return f"NoUAC_{name}"


def create_scheduled_task(exe_path: str, task_name: str, working_dir: str = None) -> tuple[bool, str]:
    """Crée la tâche planifiée via un fichier XML (sans déclencheur)."""
    if working_dir is None:
        working_dir = str(Path(exe_path).parent)

    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Lancer {task_name} sans popup UAC</Description>
  </RegistrationInfo>
  <Triggers/>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{exe_path}"</Command>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    # Écriture du XML dans un fichier temporaire en UTF-16 (requis par schtasks)
    import tempfile
    tmp = Path(tempfile.mktemp(suffix=".xml"))
    try:
        tmp.write_text(xml_content, encoding="utf-16")

        cmd = [
            "schtasks", "/create",
            "/tn", task_name,
            "/xml", str(tmp),
            "/f"
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if result.returncode == 0:
            return True, "Tâche planifiée créée avec succès."
        else:
            return False, f"Erreur schtasks:\n{result.stderr or result.stdout}"
    except FileNotFoundError:
        return False, "Commande 'schtasks' introuvable. Êtes-vous sur Windows ?"
    except Exception as e:
        return False, f"Exception inattendue : {e}"
    finally:
        tmp.unlink(missing_ok=True)


def get_desktop_path() -> Path:
    """Récupère le chemin du bureau, même s'il est déplacé."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        return Path(winreg.QueryValueEx(key, "Desktop")[0])
    except Exception:
        return Path.home() / "Desktop"


def create_desktop_shortcut(task_name: str, game_name: str, exe_path: str) -> tuple[bool, str]:
    """Crée un vrai raccourci .lnk sur le bureau via PowerShell (sans dépendance externe)."""
    try:
        desktop = get_desktop_path()
        shortcut_path = desktop / f"{game_name}.lnk"

        sc_path = str(shortcut_path).replace("'", "''")
        ex_path = exe_path.replace("'", "''")
        tn = task_name.replace('"', '`"')

        ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut('{sc_path}')
$sc.TargetPath       = 'C:\\Windows\\System32\\schtasks.exe'
$sc.Arguments        = '/run /tn "{tn}"'
$sc.WorkingDirectory = 'C:\\Windows\\System32'
$sc.WindowStyle      = 7
$sc.IconLocation     = '{ex_path},0'
$sc.Description      = 'Lancer {game_name} sans popup UAC'
$sc.Save()
"""
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

        if result.returncode != 0:
            return False, f"Erreur PowerShell :\n{result.stderr or result.stdout}"

        return True, str(shortcut_path)

    except Exception as e:
        return False, f"Erreur création raccourci : {e}"


def delete_scheduled_task(task_name: str) -> tuple[bool, str]:
    """Supprime une tâche planifiée existante."""
    cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            return True, "Tâche supprimée."
        return False, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)


# ─── Interface graphique ──────────────────────────────────────────────────────

class App(tk.Tk):

    ACCENT = "#5B5BD6"
    ACCENT_HOVER = "#4747C2"
    BG = "#F8F8FC"
    CARD_BG = "#FFFFFF"
    TEXT = "#18181B"
    MUTED = "#71717A"
    BORDER = "#E4E4E7"
    SUCCESS_BG = "#F0FDF4"
    SUCCESS_FG = "#166534"
    ERROR_BG = "#FFF1F2"
    ERROR_FG = "#9F1239"
    RADIUS = 10

    def __init__(self):
        super().__init__()
        self.title("NoUAC Shortcut")
        self.geometry("560x620")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.iconbitmap(default='')

        self.exe_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.task_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.status_type = "idle"

        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg=self.ACCENT)
        header.pack(fill="x")

        tk.Label(
            header,
            text="💻 NoUAC Shortcut",
            font=("Segoe UI", 15, "bold"),
            bg=self.ACCENT, fg="white",
            pady=18, padx=24
        ).pack(side="left")

        tk.Label(
            header,
            text="L'UAC reste actif pour le reste du système",
            font=("Segoe UI", 9),
            bg=self.ACCENT, fg="#C7C7FF",
            padx=24
        ).pack(side="right", anchor="s", pady=(0, 20))

        body = tk.Frame(self, bg=self.BG, padx=28, pady=24)
        body.pack(fill="both", expand=True)

        self._section(body, "1. Choisir l'exécutable")

        exe_row = tk.Frame(body, bg=self.BG)
        exe_row.pack(fill="x", pady=(6, 0))

        self.exe_entry = tk.Entry(
            exe_row, textvariable=self.exe_var,
            font=("Segoe UI", 10), relief="flat",
            bg=self.CARD_BG, fg=self.TEXT,
            insertbackground=self.TEXT,
            highlightthickness=1, highlightbackground=self.BORDER,
            highlightcolor=self.ACCENT
        )
        self.exe_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))

        self._btn(exe_row, "Parcourir…", self._browse_exe, small=True).pack(side="right")

        self._section(body, "2. Nom du raccourci sur le bureau", top=20)

        self.name_entry = tk.Entry(
            body, textvariable=self.name_var,
            font=("Segoe UI", 10), relief="flat",
            bg=self.CARD_BG, fg=self.TEXT,
            insertbackground=self.TEXT,
            highlightthickness=1, highlightbackground=self.BORDER,
            highlightcolor=self.ACCENT
        )
        self.name_entry.pack(fill="x", ipady=7, pady=(6, 0))

        self._section(body, "3. Nom de la tâche planifiée (optionnel)", top=20)

        self.task_entry = tk.Entry(
            body, textvariable=self.task_var,
            font=("Segoe UI", 10), relief="flat",
            bg=self.CARD_BG, fg=self.TEXT,
            insertbackground=self.TEXT,
            highlightthickness=1, highlightbackground=self.BORDER,
            highlightcolor=self.ACCENT
        )
        self.task_entry.pack(fill="x", ipady=7, pady=(6, 0))

        tk.Label(
            body,
            text="Laissez vide pour générer automatiquement depuis le nom du programme.",
            font=("Segoe UI", 8), fg=self.MUTED, bg=self.BG, anchor="w"
        ).pack(fill="x", pady=(3, 0))

        sep = tk.Frame(body, bg=self.BORDER, height=1)
        sep.pack(fill="x", pady=22)

        btn_frame = tk.Frame(body, bg=self.BG)
        btn_frame.pack(fill="x")

        self.go_btn = self._btn(btn_frame, "✅  Créer la tâche et le raccourci", self._run, big=True)
        self.go_btn.pack(fill="x")

        self._btn(btn_frame, "📋  Ouvrir le Gestionnaire de tâches", self._open_task_scheduler).pack(fill="x", pady=(8, 0))

        self.status_frame = tk.Frame(body, bg=self.BG)
        self.status_frame.pack(fill="x", pady=(16, 0))

        self.status_label = tk.Label(
            self.status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            bg=self.BG, fg=self.MUTED,
            wraplength=500, justify="left", anchor="w"
        )
        self.status_label.pack(fill="x")

        footer = tk.Frame(self, bg=self.BG, pady=8)
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text="Nécessite des droits administrateur • L'UAC reste actif pour tout le reste du système",
            font=("Segoe UI", 8), fg=self.MUTED, bg=self.BG
        ).pack()

    def _section(self, parent, text, top=0):
        tk.Label(
            parent, text=text,
            font=("Segoe UI", 9, "bold"),
            fg=self.TEXT, bg=self.BG, anchor="w"
        ).pack(fill="x", pady=(top, 0))

    def _btn(self, parent, text, command, small=False, big=False):
        font_size = 9 if small else (11 if big else 10)
        pady = 4 if small else (10 if big else 6)
        btn = tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", font_size, "bold" if big else "normal"),
            bg=self.ACCENT, fg="white",
            activebackground=self.ACCENT_HOVER, activeforeground="white",
            relief="flat", cursor="hand2",
            padx=14, pady=pady,
            bd=0
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=self.ACCENT_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.ACCENT))
        return btn

    def _browse_exe(self):
        path = filedialog.askopenfilename(
            title="Choisir l'exécutable du jeu",
            filetypes=[("Exécutables Windows", "*.exe"), ("Tous les fichiers", "*.*")]
        )
        if path:
            self.exe_var.set(path)
            game_name = Path(path).stem
            if not self.name_var.get():
                self.name_var.set(game_name)
            if not self.task_var.get():
                self.task_var.set(sanitize_task_name(path))

    def _set_status(self, msg, kind="idle"):
        self.status_type = kind
        self.status_var.set(msg)
        if kind == "success":
            self.status_label.config(fg=self.SUCCESS_FG, bg=self.BG)
            self.status_frame.config(bg=self.BG)
        elif kind == "error":
            self.status_label.config(fg=self.ERROR_FG, bg=self.BG)
            self.status_frame.config(bg=self.BG)
        else:
            self.status_label.config(fg=self.MUTED, bg=self.BG)

    def _open_task_scheduler(self):
        subprocess.Popen(["taskschd.msc"], shell=True)

    def _run(self):
        exe_path = self.exe_var.get().strip()
        game_name = self.name_var.get().strip()
        task_name = self.task_var.get().strip()

        if not exe_path:
            self._set_status("❌ Veuillez sélectionner un exécutable.", "error")
            return
        if not os.path.isfile(exe_path):
            self._set_status(f"❌ Fichier introuvable :\n{exe_path}", "error")
            return
        if not game_name:
            self._set_status("❌ Veuillez entrer un nom pour le raccourci.", "error")
            return

        if not task_name:
            task_name = sanitize_task_name(exe_path)
            self.task_var.set(task_name)

        self._set_status("⏳ Création de la tâche planifiée…", "idle")
        self.update_idletasks()

        ok, msg = create_scheduled_task(exe_path, task_name)
        if not ok:
            self._set_status(f"❌ Tâche planifiée : {msg}", "error")
            return

        ok2, result = create_desktop_shortcut(task_name, game_name, exe_path)
        if not ok2:
            self._set_status(f"⚠️  Tâche créée mais raccourci échoué :\n{result}", "error")
            return

        self._set_status(
            f"✅ Tout est prêt !\n"
            f"Tâche : «{task_name}»\n"
            f"Raccourci : {result}\n\n"
            f"Double-cliquez sur le raccourci du bureau pour lancer le jeu sans popup UAC.",
            "success"
        )


# ─── Point d'entrée ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform == "win32" and not is_admin():
        answer = messagebox.askyesno(
            "Droits administrateur requis",
            "Ce programme doit être lancé en tant qu'administrateur pour créer\n"
            "une tâche planifiée avec droits élevés.\n\n"
            "Relancer maintenant avec élévation UAC ?",
            icon="warning"
        )
        if answer:
            run_as_admin()
        else:
            sys.exit()

    app = App()
    app.mainloop()