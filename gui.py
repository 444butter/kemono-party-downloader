#!/usr/bin/python3
import threading
import tkinter as tk
import tkinter.ttk as ttk
from pygubu.widgets.pathchooserinput import PathChooserInput
from pygubu.widgets.scrolledframe import ScrolledFrame
from main import *
from tkinter.constants import END, TRUE
import datetime, time


class App:
    def __init__(self, master=None, translator=None):
        self.thread = threading.Thread(target=self.get_usr)

        self.artist = None
        _ = translator
        if translator is None:

            def _(x):
                return x

        # build ui
        self.root = ttk.Frame(master)
        self.root.configure(height=600, width=800)
        # set the icon

        self.top_frame = ttk.Frame(self.root)
        self.top_frame.configure(height=200, width=200)
        self.get = ttk.Label(self.top_frame)
        self.get.configure(text=_("Artist Url"))
        self.get.pack(side="left")
        self.artist_url_entry = ttk.Entry(self.top_frame)
        self.artistURL = tk.StringVar()
        self.artist_url_entry.configure(
            font="TkDefaultFont", state="normal", textvariable=self.artistURL
        )
        self.artist_url_entry.pack(
            expand="true", fill="y", ipadx=225, padx=10, pady=10, side="left"
        )
        self.get_usr_btn = ttk.Button(self.top_frame)
        self.get_usr_btn.configure(default="normal", text=_("Start"))
        self.get_usr_btn.pack(fill="both", ipadx=5, padx=10, pady=10, side="left")
        self.get_usr_btn.configure(command=self.start_btn)
        self.get_usr_btn.bind("<1>", self.callback, add="")
        self.top_frame.pack(side="top")

        self.path_frame = ttk.Labelframe(self.root)
        self.path_frame.configure(height=200, text=_("Download Location"), width=200)
        self.down_path = PathChooserInput(self.path_frame)
        self.download_location = tk.StringVar(value="C:\\Downloads\\")
        self.down_path.configure(
            initialdir="C:\\Downloads\\",
            mustexist="true",
            path="C:\\Downloads\\",
            state="normal",
            textvariable=self.download_location,
            type="directory",
        )
        self.down_path.pack(expand="true", fill="x", ipadx=285, side="bottom")
        self.path_frame.pack(side="top")

        downloadprog_frame = ttk.Frame(self.root)
        downloadprog_frame.configure(height=200, width=200)
        self.download_caption = ttk.Label(downloadprog_frame)
        self.download_caption.configure(text=_("Downloaded 0/0"))
        self.download_caption.pack(side="top")
        self.file_pbar = ttk.Progressbar(downloadprog_frame)
        self.file_pbar_prog = tk.IntVar(value=_(0))
        self.progressbar2_prog = tk.IntVar(value=_(0))
        self.file_pbar.configure(
            orient="horizontal", value=0, variable=self.file_pbar_prog
        )
        self.file_pbar.pack(ipadx=320, padx=10, side="top")
        self.progressbar2 = ttk.Progressbar(downloadprog_frame)
        self.progressbar2.configure(
            orient="horizontal", value=0, variable=self.progressbar2_prog
        )
        self.progressbar2.pack(ipadx=320, padx=10, side="top")
        downloadprog_frame.pack(pady=10, side="top")

        self.log_frame = ScrolledFrame(self.root, scrolltype="both")
        self.log_frame.configure(usemousewheel=True)
        self.logs_label = ttk.Label(self.log_frame.innerframe)
        self.logs_label.configure(text=_("Logs"))
        self.logs_label.pack(anchor="w", side="top")
        self.log_textbox = tk.Text(self.log_frame.innerframe)
        self.log_textbox.configure(height=10, state="disabled", width=50)
        self.log_textbox.pack(expand="true", fill="both", side="top")
        self.log_frame.pack(
            expand="false", fill="both", ipadx=250, padx=10, pady=10, side="top"
        )
        self.root.pack(side="top")

        # Main widget
        self.mainwindow = self.root

    def run(self):
        self.downloader = Downloader(logger=self.log_togui)
        self.mainwindow.mainloop()

    def get_usr(self):
        # self.artist = get_user(self.artistURL.get())
        site = parse_url(self.artistURL.get())
        if not site:
            self.log_togui("Invalid URL")
            return
        self.downloader.get_user(site)
        self.artist = self.downloader.artist
        self.log_togui("Artist: " + self.artist.name)
        self.log_togui("Total Posts: " + str(self.artist.total_posts))
        self.downloader.download_location = self.download_location.get()
        self.downloader.download(update_progress=self.update_progress)
        self.log_togui("Download Complete")
        self.update_progress(
            {
                "percent": 100,
                "total_percent": 100,
            }
        )

    def callback(self, event=None):
        pass

    def update_progress(self, progress):
        self.file_pbar_prog = progress["percent"]
        self.file_pbar["value"] = progress["percent"]
        self.progressbar2_prog = progress["total_percent"]
        self.progressbar2["value"] = progress["total_percent"]
        self.download_caption["text"] = f"Downloaded ({progress['percent']}%)"

    def start_btn(self):
        self.get_usr_btn["state"] = "disabled"
        self.get_usr_btn["text"] = "Downloading"
        if self.thread._is_stopped:
            self.thread = threading.Thread(target=self.get_usr)
        self.thread.start()
        self.check_status()

    def check_status(self):
        if not self.thread.is_alive():
            self.get_usr_btn["state"] = "normal"
            self.get_usr_btn["text"] = "Start"
        else:
            self.root.after(500, self.check_status)

    def log_togui(self, message):
        self.log_textbox.configure(state="normal")
        autoscroll = False
        ts = datetime.datetime.fromtimestamp(time.time()).strftime("%H:%M:%S || ")
        if self.log_textbox.yview()[1] == 1:
            autoscroll = True
        self.log_textbox.insert(END, ts + message + "\n", type)
        if autoscroll:
            self.log_textbox.see(END)
        self.log_textbox.configure(state="disabled")


def main():
    root = tk.Tk()
    root.title("Kemono Downloader")
    # if the file favicon.ico exists
    if os.path.isfile("favicon.ico"):
        root.iconbitmap("favicon.ico")
    else:
        root.iconbitmap("kemonodl.exe")
    root.resizable(False, False)
    app = App(root)
    app.run()


if __name__ == "__main__":
    main()
