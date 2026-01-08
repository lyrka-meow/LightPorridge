#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import subprocess
import os
import shutil
import time

# Глобальные переменные
install_data = {
    "method": None,
    "user_name": "",
    "host_name": "",
    "password": "",
    "device": ""
}

def get_install_drive():
    possible_drives = ["/dev/vda", "/dev/sda", "/dev/nvme0n1"]
    for drive in possible_drives:
        if os.path.exists(drive):
            return drive
    return "/dev/sda"

install_data["device"] = get_install_drive()

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LightPorridge Installer")
        self.attributes('-fullscreen', True)
        
        self.container = tk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        # Добавлена WifiPage
        for F in (WelcomePage, WifiPage, PartitionPage, UserInfoPage, InstallingPage):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame("WelcomePage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if page_name == "WifiPage":
            frame.scan_networks() # Автосканирование при открытии

    def exit_installer(self):
        if messagebox.askokcancel("Выход", "Выйти в Live-режим?"):
            self.destroy()

class WelcomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        label = tk.Label(self, text="Добро пожаловать в LightPorridge", font=("Arial", 28, "bold"))
        label.pack(pady=80)
        
        # Проверка сети (информативно)
        self.lbl_net = tk.Label(self, text="Проверка сети...", font=("Arial", 12), fg="gray")
        self.lbl_net.pack(pady=10)
        self.check_net()
        
        btn_next = tk.Button(self, text="Далее", command=lambda: controller.show_frame("WifiPage"), font=("Arial", 14), width=20)
        btn_next.pack(pady=40)

    def check_net(self):
        # Простой пинг
        res = subprocess.call(["ping", "-c", "1", "8.8.8.8"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res == 0:
            self.lbl_net.config(text="Интернет: ДОСТУПЕН", fg="green")
        else:
            self.lbl_net.config(text="Интернет: НЕДОСТУПЕН (Настройте на след. шаге)", fg="red")
        self.after(5000, self.check_net)

class WifiPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        label = tk.Label(self, text="Настройка сети (Wi-Fi)", font=("Arial", 24))
        label.pack(pady=20)
        
        # Список сетей
        self.tree = ttk.Treeview(self, columns=('SSID', 'Signal'), show='headings', height=10)
        self.tree.heading('SSID', text='Сеть')
        self.tree.heading('Signal', text='Сигнал')
        self.tree.column('SSID', width=300)
        self.tree.column('Signal', width=100)
        self.tree.pack(pady=10)
        
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        
        btn_scan = tk.Button(btn_frame, text="Сканировать", command=self.scan_networks)
        btn_scan.pack(side="left", padx=10)
        
        btn_connect = tk.Button(btn_frame, text="Подключиться", command=self.connect_wifi)
        btn_connect.pack(side="left", padx=10)
        
        self.lbl_status = tk.Label(self, text="", font=("Arial", 12))
        self.lbl_status.pack(pady=10)

        btn_next = tk.Button(self, text="Далее", command=lambda: controller.show_frame("PartitionPage"), font=("Arial", 14), width=20)
        btn_next.pack(pady=30)

    def scan_networks(self):
        self.lbl_status.config(text="Сканирование...", fg="blue")
        self.update()
        try:
            # nmcli dev wifi list
            # SSID SIGNAL BARS SECURITY
            cmd = "nmcli -f SSID,SIGNAL dev wifi list"
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            
            # Очистка таблицы
            for i in self.tree.get_children():
                self.tree.delete(i)
                
            lines = output.split('\n')
            for line in lines[1:]: # Пропуск заголовка
                if not line.strip(): continue
                # Парсинг сложный из-за пробелов в SSID, берем упрощенно
                parts = line.rsplit(maxsplit=1) # Signal обычно в конце
                if len(parts) == 2:
                    ssid = parts[0].strip()
                    signal = parts[1].strip()
                    if ssid and ssid != "--":
                         self.tree.insert('', 'end', values=(ssid, signal))
            
            self.lbl_status.config(text="Сканирование завершено", fg="green")
            
        except Exception as e:
            self.lbl_status.config(text=f"Ошибка сканирования: {e}", fg="red")

    def connect_wifi(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Wifi", "Выберите сеть!")
            return
            
        ssid = self.tree.item(selected[0])['values'][0]
        password = simpledialog.askstring("Пароль", f"Введите пароль для {ssid}", show='*')
        
        if password is not None:
            self.lbl_status.config(text=f"Подключение к {ssid}...", fg="blue")
            self.update()
            try:
                subprocess.check_call(f"nmcli dev wifi connect '{ssid}' password '{password}'", shell=True)
                messagebox.showinfo("Успех", f"Подключено к {ssid}!")
                self.lbl_status.config(text=f"Подключено к {ssid}", fg="green")
            except subprocess.CalledProcessError:
                messagebox.showerror("Ошибка", "Не удалось подключиться. Проверьте пароль.")
                self.lbl_status.config(text="Ошибка подключения", fg="red")

class PartitionPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        label = tk.Label(self, text=f"Разметка диска (Цель: {install_data['device']})", font=("Arial", 24))
        label.pack(pady=40)
        
        self.var = tk.StringVar(value="erase")
        
        modes = [
            ("Стереть диск и установить (РЕКОМЕНДУЕТСЯ)", "erase"),
            ("Установить рядом (Экспериментально - не работает)", "alongside"),
        ]
        
        for text, mode in modes:
            b = tk.Radiobutton(self, text=text, variable=self.var, value=mode, font=("Arial", 16), indicatoron=0, width=40, pady=10)
            b.pack(pady=10)
            
        btn_next = tk.Button(self, text="Далее", command=self.save_and_next, font=("Arial", 14), width=20)
        btn_next.pack(pady=50)

    def save_and_next(self):
        method = self.var.get()
        if method != "erase":
            messagebox.showwarning("Внимание", "Пока реализован только режим 'Стереть диск'. Пожалуйста, выберите его для теста.")
            return
        install_data["method"] = method
        self.controller.show_frame("UserInfoPage")

class UserInfoPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        label = tk.Label(self, text="Пользователь", font=("Arial", 24))
        label.pack(pady=40)
        
        form = tk.Frame(self)
        form.pack()
        
        tk.Label(form, text="Имя:", font=("Arial", 14)).grid(row=0, column=0, sticky="e")
        self.entry_name = tk.Entry(form, font=("Arial", 14))
        self.entry_name.grid(row=0, column=1, pady=10)
        
        tk.Label(form, text="Хост:", font=("Arial", 14)).grid(row=1, column=0, sticky="e")
        self.entry_host = tk.Entry(form, font=("Arial", 14))
        self.entry_host.grid(row=1, column=1, pady=10)
        
        tk.Label(form, text="Пароль:", font=("Arial", 14)).grid(row=2, column=0, sticky="e")
        self.entry_pass = tk.Entry(form, font=("Arial", 14), show="*")
        self.entry_pass.grid(row=2, column=1, pady=10)
        
        btn = tk.Button(self, text="Установить", command=self.validate, font=("Arial", 14, "bold"), bg="red", fg="white")
        btn.pack(pady=40)

    def validate(self):
        if not self.entry_name.get() or not self.entry_host.get() or not self.entry_pass.get():
            messagebox.showerror("Err", "Заполните поля")
            return
        install_data["user_name"] = self.entry_name.get()
        install_data["host_name"] = self.entry_host.get()
        install_data["password"] = self.entry_pass.get()
        
        if messagebox.askyesno("Install", "ВНИМАНИЕ! ВСЕ ДАННЫЕ НА ДИСКЕ БУДУТ УДАЛЕНЫ!\nПродолжить?"):
            self.controller.show_frame("InstallingPage")
            self.controller.frames["InstallingPage"].start_installation()

class InstallingPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.label = tk.Label(self, text="Идет установка...", font=("Arial", 24))
        self.label.pack(pady=20)
        self.log = tk.Text(self, height=20, width=90)
        self.log.pack()

    def log_msg(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.update()

    def run(self, cmd):
        self.log_msg(f"CMD: {cmd}")
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            self.log_msg(f"ERROR: {e}")
            messagebox.showerror("Ошибка", f"Команда не удалась:\n{cmd}")
            raise e

    def start_installation(self):
        dev = install_data["device"]
        user = install_data["user_name"]
        pw = install_data["password"]
        host = install_data["host_name"]
        
        try:
            # 1. Разметка (Parted)
            self.log_msg(f"--- Форматирование {dev} ---")
            self.run(f"parted -s {dev} mklabel gpt")
            self.run(f"parted -s {dev} mkpart ESP fat32 1MiB 513MiB")
            self.run(f"parted -s {dev} set 1 boot on")
            self.run(f"parted -s {dev} mkpart primary ext4 513MiB 100%")
            
            part_efi = f"{dev}1" if "nvme" not in dev else f"{dev}p1"
            part_root = f"{dev}2" if "nvme" not in dev else f"{dev}p2"
            
            self.run(f"mkfs.fat -F32 {part_efi}")
            self.run(f"mkfs.ext4 -F {part_root}")
            
            # 2. Монтирование
            self.log_msg("--- Монтирование ---")
            self.run(f"mount {part_root} /mnt")
            self.run(f"mkdir -p /mnt/boot")
            self.run(f"mount {part_efi} /mnt/boot")
            
            # 3. Pacstrap
            self.log_msg("--- Установка системы (Pacstrap) ---")
            pkgs = "base base-devel linux-cachyos linux-firmware grub efibootmgr networkmanager git qtile kitty tmate python-psutil python-gobject gtk3 sudo nano vim os-prober"
            self.run(f"pacstrap /mnt {pkgs}")
            
            # 4. Fstab
            self.log_msg("--- Genfstab ---")
            self.run("genfstab -U /mnt >> /mnt/etc/fstab")
            
            # 5. Настройка внутри Chroot
            self.log_msg("--- Настройка системы ---")
            
            setup_script = f"""
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
hwclock --systohc
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
echo "ru_RU.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG=ru_RU.UTF-8" > /etc/locale.conf
echo "{host}" > /etc/hostname
echo "127.0.0.1 localhost" >> /etc/hosts
echo "127.0.1.1 {host}.localdomain {host}" >> /etc/hosts

useradd -m -G wheel -s /bin/bash {user}
echo "{user}:{pw}" | chpasswd
echo "root:{pw}" | chpasswd

echo "%wheel ALL=(ALL:ALL) ALL" >> /etc/sudoers

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=LightPorridge
sed -i 's/^#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg

systemctl enable NetworkManager

mkdir -p /home/{user}/.config/qtile
chown -R {user}:{user} /home/{user}/.config
"""
            with open("/mnt/setup.sh", "w") as f:
                f.write(setup_script)
            
            self.run("chmod +x /mnt/setup.sh")
            self.run("arch-chroot /mnt /setup.sh")
            self.run("rm /mnt/setup.sh")
            
            # 6. Копирование конфигов
            self.log_msg("--- Копирование конфигов ---")
            try:
                src_cfg = "/etc/skel/.config/qtile/config.py"
                dst_cfg = f"/mnt/home/{user}/.config/qtile/config.py"
                
                with open(src_cfg, 'r') as f:
                    cfg_content = f.read()
                
                cfg_content = cfg_content.replace("subprocess.Popen(['sudo', '/usr/bin/python3', home + '/installer.py'])", "# Installer removed")
                
                with open(dst_cfg, 'w') as f:
                    f.write(cfg_content)
                    
                self.run(f"chown {user}:{user} {dst_cfg}")
                
                with open(f"/mnt/home/{user}/.xinitrc", "w") as f:
                    f.write("#!/bin/sh\nexec qtile start\n")
                self.run(f"chmod +x /mnt/home/{user}/.xinitrc")
                self.run(f"chown {user}:{user} /mnt/home/{user}/.xinitrc")
                
            except Exception as e:
                 self.log_msg(f"Warning copying configs: {e}")

            self.log_msg("--- УСТАНОВКА ЗАВЕРШЕНА! ---")
            messagebox.showinfo("Готово", "Система установлена!\nПерезагрузитесь.")
            self.run("reboot")
            
        except Exception as e:
            self.log_msg(f"CRITICAL ERROR: {e}")
            messagebox.showerror("Fatal", str(e))

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
