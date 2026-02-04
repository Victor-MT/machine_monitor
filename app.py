import tkinter as tk
import psutil
import time
import sys

# ----------------------------
# CONFIG
# ----------------------------
UPDATE_MS = 1000
WINDOW_MIN_WIDTH = 470
WINDOW_MIN_HEIGHT = 200

CPU_WARN = 80.0
RAM_WARN = 85.0
DISK_MB_S_WARN = 50.0     # read+write (MB/s)
NET_KB_S_WARN = 2000.0    # down+up (KB/s)

BG = "#0f111a"
FG = "#e6e6e6"
SUB = "#a9b1d6"
WARN = "#f7768e"
OK = "#9ece6a"

IS_WINDOWS = sys.platform.startswith("win")
TITLE_FONT = ("Segoe UI", 12, "bold") if IS_WINDOWS else ("DejaVu Sans", 12, "bold")
TEXT_FONT = ("Consolas", 11) if IS_WINDOWS else ("DejaVu Sans Mono", 11)


def bytes_to_gb(b): return b / (1024 ** 3)
def bytes_to_mb(b): return b / (1024 ** 2)
def bytes_to_kb(b): return b / 1024


class MiniMonitor:
    def __init__(self):
        self._drag_x = 0        
        self._drag_y = 0

        self.root = tk.Tk()
        self.root.title("Monitor")
        self.root.update_idletasks()
        self.root.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}+12+12")
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        if IS_WINDOWS:
            # Borderless mode behaves well on native Windows.
            self.root.overrideredirect(True)
            self.root.bind("<ButtonPress-1>", self._start_move)
            self.root.bind("<B1-Motion>", self._do_move)
        else:
            # On Linux/WSL, overrideredirect may clip text in some compositors/X servers.
            self.root.resizable(False, False)
       


        # Prime CPU
        psutil.cpu_percent(interval=None)

        # Baselines for rate calculation
        self.prev_disk = psutil.disk_io_counters()
        self.prev_net = psutil.net_io_counters()
        self.prev_t = time.time()

        self.frame = tk.Frame(self.root, bg=BG)
        self.frame.pack(fill="both", expand=True, padx=14, pady=12)

        self.title = tk.Label(
            self.frame, text="Recursos do Sistema",
            fg=FG, bg=BG, font=TITLE_FONT
        )
        self.title.pack(anchor="w")

        self.hint = tk.Label(
            self.frame, text="Atualiza a cada 1s",
            fg=SUB, bg=BG, font=(TITLE_FONT[0], 9)
        )
        self.hint.pack(anchor="w", pady=(2, 10))

        self.cpu_lbl = self._line("CPU")
        self.ram_lbl = self._line("RAM")
        self.disk_lbl = self._line("Disco")
        self.net_lbl = self._line("Rede")

        self.status = tk.Label(
            self.frame, text="Status: OK",
            fg=OK, bg=BG, font=(TITLE_FONT[0], 10, "bold")
        )
        self.status.pack(anchor="w", pady=(10, 0))

        self.update()

    def _fit_to_content(self, force=False):
        self.root.update_idletasks()

        req_w = self.frame.winfo_reqwidth() + 28
        req_h = self.frame.winfo_reqheight() + 24

        target_w = max(WINDOW_MIN_WIDTH, req_w)
        target_h = max(WINDOW_MIN_HEIGHT, req_h)

        cur_w = self.root.winfo_width()
        cur_h = self.root.winfo_height()

        if force or target_w > cur_w or target_h > cur_h:
            x, y = self.root.winfo_x(), self.root.winfo_y()
            self.root.geometry(f"{target_w}x{target_h}+{x}+{y}")

    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_move(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")


    def _line(self, _):
        lbl = tk.Label(
            self.frame,
            text="--",
            fg=FG, bg=BG,
            font=TEXT_FONT,
            anchor="w",
            justify="left"
        )
        lbl.pack(anchor="w", pady=2)
        return lbl

    def update(self):
        now = time.time()
        dt = max(0.001, now - self.prev_t)

        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()

        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()

        d_read = (disk.read_bytes - self.prev_disk.read_bytes) / dt
        d_write = (disk.write_bytes - self.prev_disk.write_bytes) / dt
        d_total_mb_s = bytes_to_mb(d_read + d_write)

        n_down = (net.bytes_recv - self.prev_net.bytes_recv) / dt
        n_up = (net.bytes_sent - self.prev_net.bytes_sent) / dt
        n_total_kb_s = bytes_to_kb(n_down + n_up)

        # update baselines
        self.prev_disk, self.prev_net, self.prev_t = disk, net, now

        cpu_hot = cpu >= CPU_WARN
        ram_hot = vm.percent >= RAM_WARN
        disk_hot = d_total_mb_s >= DISK_MB_S_WARN
        net_hot = n_total_kb_s >= NET_KB_S_WARN

        # self.cpu_lbl.config(
        #     text=f"{'🔥' if cpu_hot else ' '} CPU  {cpu:5.1f}%",
        #     fg=WARN if cpu_hot else FG
        # )

        self.cpu_lbl.config(
            text= f"{'🔥' if ram_hot else ' '} RAM {vm.percent:5.1f}% "
                f"({bytes_to_gb(vm.used):.1f}/{bytes_to_gb(vm.total):.1f} GB) | "
                f"{'🔥' if cpu_hot else ' '} CPU {cpu:5.1f}%",
            fg=WARN if (cpu_hot or ram_hot) else FG
        )
        self.ram_lbl.config(
            text=f"{'🔥' if ram_hot else ' '} RAM  {vm.percent:5.1f}%  ({bytes_to_gb(vm.used):.1f}/{bytes_to_gb(vm.total):.1f} GB)",
            fg=WARN if ram_hot else FG
        )
        self.ram_lbl.pack_forget()

        self.disk_lbl.config(
            text=f"{'🔥' if disk_hot else ' '} Disco R {bytes_to_mb(d_read):6.1f} MB/s | W {bytes_to_mb(d_write):6.1f} MB/s",
            fg=WARN if disk_hot else FG
        )
        self.net_lbl.config(
            text=f"{'🔥' if net_hot else ' '} Rede  ↓ {bytes_to_kb(n_down):7.0f} KB/s | ↑ {bytes_to_kb(n_up):7.0f} KB/s",
            fg=WARN if net_hot else FG
        )

        if cpu_hot or ram_hot or disk_hot or net_hot:
            parts = []
            if cpu_hot: parts.append("CPU")
            if ram_hot: parts.append("RAM")
            if disk_hot: parts.append("Disco")
            if net_hot: parts.append("Rede")
            self.status.config(text=f"Status: PICO em {', '.join(parts)}", fg=WARN)
        else:
            self.status.config(text="Status: OK", fg=OK)

        self._fit_to_content()
        self.root.after(UPDATE_MS, self.update)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MiniMonitor().run()
