import tkinter as tk
from tkinter import *
from tkinter import ttk, messagebox
import psycopg2
import os
from tkinter.filedialog import askopenfile
import requests
from bs4 import BeautifulSoup
from cefpython3 import cefpython as cef
import folium
import ctypes
from datetime import datetime

# On travaille dans le répertoire courant (le fichier info.txt sera créé ici)
conn = None
Fichier = ''

def connexion():
    global conn
    host = localhost_entry.get()
    dbname = dbname_entry.get()
    user = login_entry.get()
    password = mot_de_passe_entry.get()

    infos = [host, dbname, user, password]
    with open("info.txt", 'w') as file:
        for line in infos:
            file.write(line + "\n")
    try:
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port="5432",
            database=dbname
        )
        messagebox.showinfo("Connexion réussie", "Connexion à la base de données établie avec succès!")
        serverframe.pack_forget()
        menu_frame.place(x=5, y=60, width=1000, height=600)
        camera_frame.place(x=5, y=20, width=580, height=350)
    except psycopg2.Error as e:
        messagebox.showerror("Erreur de connexion", f"Échec de la connexion à la base de données : {e}")

def get_table():
    """Retourne le nom de la table 'cameras' si elle existe, sinon affiche une erreur."""
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='cameras';")
    table_existante = cur.fetchone()
    cur.close()
    if table_existante is not None:
        return table_existante[0]
    else:
        messagebox.showerror("Erreur", "La table 'cameras' n'existe pas !")
        return None

def ajouter_cam():
    global conn
    # On récupère les valeurs saisies
    num = id_entry.get().strip()
    Loc = localisation_entry.get().strip()
    Arr = Arr_entry.get().strip()
    date_val = date_entry.get().strip()
    longitude = longitude_entry.get().strip()
    latitude = latitude_entry.get().strip()
    altitude = altitude_entry.get().strip()
    style = style_entry.get().strip()

    # On cherche la table 'cameras'
    nom_table = get_table()
    rep = True
    if nom_table is None:
        rep = False
        messagebox.showerror("Erreur", "Aucune table 'cameras' disponible.")
    if rep:
        try:
            cur = conn.cursor()
            cur.execute(
                f"""INSERT INTO {nom_table}
                (num_camera, localisation, arrondissement, date_installation, longitude, latitude, altitude, style)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);""",
                (num, Loc, Arr, date_val, longitude, latitude, altitude, style)
            )
            conn.commit()
            cur.close()
            messagebox.showinfo("Succès", "Données ajoutées avec succès")
        except psycopg2.Error as e:
            messagebox.showerror("Erreur", f"Requête SQL incorrecte : {e}")

def retour_au_menu():
    carte_frame.place_forget()
    menu_frame.place(x=5, y=60, width=1000, height=600)




def ouvrir():
    global Fichier
    listeextensions = [("Fichiers textes", "*.kml")]
    fichier = askopenfile(filetypes=listeextensions, defaultextension=listeextensions)
    # On part du principe que l'utilisateur sélectionne un fichier
    Fichier = fichier.name.split(os.sep)[-1]
    but_import.place(x=800, y=150)

def importer():
    global Fichier, conn
    rep = True  # Indique si l'on poursuit l'import
    try:
        with open(Fichier, 'r', encoding="utf-8") as file:
            soup = BeautifulSoup(file, 'xml')
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'ouvrir le fichier: {e}")
        rep = False

    cur = conn.cursor()
    # On recherche spécifiquement la table 'cameras'
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='cameras';")
    table_exists = get_table()
    if table_exists:
        rep = messagebox.askyesno("Autorisation", "La table 'cameras' existe déjà. Voulez-vous la supprimer et la recréer ?")
        if rep:
            cur.execute("DROP TABLE public.cameras")
            cur.execute("""
                CREATE TABLE cameras (
                    id SERIAL PRIMARY KEY,
                    num_camera INTEGER,
                    localisation TEXT,
                    arrondissement TEXT,
                    date_installation DATE,
                    longitude FLOAT,
                    latitude FLOAT,
                    altitude FLOAT,
                    style TEXT
                );
            """)
            messagebox.showinfo("Succès", "La table a été supprimée et recréée")
        else:
            messagebox.showwarning("Annulation", "Import annulé car la table existe déjà et n'a pas été supprimée")
            rep = False

    else:
        cur.execute("""
            CREATE TABLE cameras (
                id SERIAL PRIMARY KEY,
                num_camera INTEGER,
                localisation TEXT,
                arrondissement TEXT,
                date_installation DATE,
                longitude FLOAT,
                latitude FLOAT,
                altitude FLOAT,
                style TEXT
            );
        """)
    conn.commit()

    if rep:
        # Extraction des données du fichier KML
        localisation = []
        arrondissement = []
        numero = []
        longitude = []
        latitude = []
        altitude = []
        date_installation = []
        style = []

        for val in soup.find_all('Data', attrs={"name": "NUMÉRO"}):
            numero.append(val.text.strip())

        for val in soup.find_all('Data', attrs={"name": "LOCALISATI"}):
            localisation.append(val.text.strip())

        for val in soup.find_all('Data', attrs={"name": "ARRONDISSE"}):
            arrondissement.append(val.text.strip())

        for val in soup.find_all('Data', attrs={"name": "MISE_EN_SE"}):
            date_text = val.text.strip()
            date_installation.append(date_text if date_text else None)

        for val in soup.find_all('styleUrl'):
            style.append(val.text.strip())

        for val in soup.find_all('coordinates'):
            coords = val.text.strip().split(',')
            longitude.append(coords[0])
            latitude.append(coords[1])
            altitude.append(coords[2] if len(coords) > 2 else None)

        for i in range(len(localisation)):
            num_val = numero[i] if numero[i].isdigit() else None
            cur.execute("""
                INSERT INTO cameras
                (num_camera, localisation, arrondissement, date_installation, longitude, latitude, altitude, style)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (num_val,
                  localisation[i],
                  arrondissement[i],
                  date_installation[i],
                  longitude[i],
                  latitude[i],
                  altitude[i],
                  style[i] if i < len(style) else None))
        conn.commit()
        messagebox.showinfo("Succès", "Données importées avec succès !")
        but_voir_carte.place(x=700, y=300)
    cur.close()

def voir_carte():
    table_name = get_table()
    rep = True
    if table_name is None:
        rep= False
        messagebox.showerror("Erreur", "Aucune table 'cameras' trouvée !")

    if rep:
        cur = conn.cursor()
        cur.execute(f"SELECT localisation, latitude, longitude, date_installation FROM {table_name};")
        data = cur.fetchall()
        cur.close()
        if not data:
            messagebox.showerror("Erreur", "Aucune donnée à afficher sur la carte.")
            rep = False

    if rep:
        # Création de la carte centrée sur le premier point
        carte = folium.Map(location=[ 48.856, 2.3522], zoom_start=13)
        for loc, lat, lon, date_installation in data:
            couleur = "red"
            year_str = "Inconnue"
            try:
                if date_installation:
                    if isinstance(date_installation, str):
                        date_obj = datetime.strptime(date_installation, "%Y-%m-%d")
                    else:
                        date_obj = date_installation
                    year = date_obj.year
                    year_str = str(year)
                    if year < 2015:
                        couleur = "blue"
                    elif year < 2018:
                       couleur = "green"
                    elif year < 2019:
                       couleur = "orange"
                    else:
                        couleur = "black"
            except Exception as e:
                print("Erreur lors du parsing de la date:", e)

            folium.Marker(
                location=[lat, lon],
                popup=f"{loc} - {year_str}",
                icon=folium.Icon(icon='camera', prefix='fa', color=couleur)
            ).add_to(carte)
        carte.save("carte.html")

        # On cache le menu et on affiche la carte dans un nouveau frame
        menu_frame.place_forget()
        btn_retour.place(x=10, y=10)
        carte_frame.place(x=5, y=60, width=1200, height=700)
        afficher_carte()

def afficher_carte():
    for widget in carte_frame.winfo_children():
        widget.destroy()
    browser_frame = BrowserFrame(carte_frame)
    browser_frame.pack(fill=tk.BOTH, expand=tk.YES)

class BrowserFrame(tk.Frame):
    def __init__(self, mainframe):
        tk.Frame.__init__(self, mainframe)
        self.browser = None
        self.bind("<Configure>", self.on_configure)
        self.focus_set()

    def embed_browser(self):
        window_info = cef.WindowInfo()
        rect = [0, 0, self.winfo_width(), self.winfo_height()]
        window_info.SetAsChild(self.winfo_id(), rect)
        self.browser = cef.CreateBrowserSync(window_info, url="file:///{}{}".format(os.getcwd(), os.sep + "carte.html"))
        self.message_loop_work()

    def message_loop_work(self):
        cef.MessageLoopWork()
        self.after(10, self.message_loop_work)

    def on_configure(self, _):
        if not self.browser:
            self.embed_browser()

def charger_info():
    if os.path.exists("info.txt"):
        with open("info.txt", "r") as file:
            data = file.readlines()
            data = [line.strip() for line in data]
            if len(data) >= 4:
                localhost_entry.insert(0, data[0])
                dbname_entry.insert(0, data[1])
                login_entry.insert(0, data[2])
                mot_de_passe_entry.insert(0, data[3])

# Création de la fenêtre principale Tkinter
window = Tk()
window.geometry("1250x800")
window.title("Application DB & Carte avec cefpython3")

label = Label(window, text="Bonjour, bienvenue sur notre application", bg='blue', fg='white', font='arial 13 bold')
label.pack()

main_Frame = Frame(window, bd=2, relief=GROOVE, bg='white')
main_Frame.place(x=10, y=60, width=700, height=300)

serverframe = LabelFrame(main_Frame, text="Server", font=('times new roman', 15), bg="white")
serverframe.place(x=10, y=60, width=400, height=200)

localhost_label = Label(serverframe, text='Localhost', font=('times new roman', 15, 'bold'), bg="white")
localhost_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
localhost_entry = Entry(serverframe, font=('times new roman', 15))
localhost_entry.grid(row=0, column=1, padx=10, pady=5)

dbname_label = Label(serverframe, text='Dbname', font=('times new roman', 15, 'bold'), bg="white")
dbname_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
dbname_entry = Entry(serverframe, font=('times new roman', 15))
dbname_entry.grid(row=1, column=1, padx=10, pady=5)

login_label = Label(serverframe, text='Login', font=('times new roman', 15, 'bold'), bg="white")
login_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
login_entry = Entry(serverframe, font=('times new roman', 15))
login_entry.grid(row=2, column=1, padx=10, pady=5)

mot_de_passe_label = Label(serverframe, text='Mot de passe', font=('times new roman', 15, 'bold'), bg="white")
mot_de_passe_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
mot_de_passe_entry = Entry(serverframe, font=('times new roman', 15), show="*")
mot_de_passe_entry.grid(row=3, column=1, padx=10, pady=5)

conn_button = Button(main_Frame, text='Se connecter', command=connexion, bg='blue', fg='white', font='arial 13 bold')
conn_button.place(x=10, y=260)

menu_frame = Frame(window, bd=2, relief=GROOVE, bg='white')

camera_frame = LabelFrame(menu_frame, text='Camera', font=('times new roman', 15), bg="white")
camera_frame.place(x=5, y=20, width=580, height=350)

localisation_label = Label(camera_frame, text='Localisation', font=('times new roman', 15, 'bold'), bg="white")
localisation_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
localisation_entry = Entry(camera_frame, font=('times new roman', 15))
localisation_entry.grid(row=0, column=1, padx=10, pady=5)

id_label = Label(camera_frame, text='Numéro de la caméra', font=('times new roman', 15, 'bold'), bg="white")
id_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
id_entry = Entry(camera_frame, font=('times new roman', 15))
id_entry.grid(row=1, column=1, padx=10, pady=5)

Arr_label = Label(camera_frame, text='Arrondissement', font=('times new roman', 15, 'bold'), bg="white")
Arr_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
Arr_entry = Entry(camera_frame, font=('times new roman', 15))
Arr_entry.grid(row=2, column=1, padx=10, pady=5)

date_label = Label(camera_frame, text='Date installation', font=('times new roman', 15, 'bold'), bg="white")
date_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
date_entry = Entry(camera_frame, font=('times new roman', 15))
date_entry.grid(row=3, column=1, padx=10, pady=5)

longitude_label = Label(camera_frame, text='Longitude', font=('times new roman', 15, 'bold'), bg="white")
longitude_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
longitude_entry = Entry(camera_frame, font=('times new roman', 15))
longitude_entry.grid(row=4, column=1, padx=10, pady=5)

latitude_label = Label(camera_frame, text='Latitude', font=('times new roman', 15, 'bold'), bg="white")
latitude_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
latitude_entry = Entry(camera_frame, font=('times new roman', 15))
latitude_entry.grid(row=5, column=1, padx=10, pady=5)

altitude_label = Label(camera_frame, text='Altitude', font=('times new roman', 15, 'bold'), bg="white")
altitude_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
altitude_entry = Entry(camera_frame, font=('times new roman', 15))
altitude_entry.grid(row=6, column=1, padx=10, pady=5)

style_label = Label(camera_frame, text='Style', font=('times new roman', 15, 'bold'), bg="white")
style_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
style_entry = Entry(camera_frame, font=('times new roman', 15))
style_entry.grid(row=7, column=1, padx=10, pady=5)

but_camera = Button(menu_frame, text='Ajouter caméra', command=ajouter_cam, bg='blue', fg='white', font='arial 13 bold')
but_camera.place(x=10, y=400)

but_ouvrir = Button(menu_frame, text='Ouvrir un fichier KML', command=ouvrir, bg='blue', fg='white', font='arial 13 bold')
but_ouvrir.place(x=800, y=70)

but_import = Button(menu_frame, text='Importer le fichier', command=importer, bg='blue', fg='white', font='arial 13 bold')
# Frame dédiée à l'affichage de la carte
carte_frame = Frame(window, bd=2, relief=GROOVE, bg='white')

but_voir_carte = Button(menu_frame, text='Voir les caméras sur carte', command=voir_carte, bg='blue', fg='white', font='arial 13 bold')
btn_retour = Button(window, text="Retour au menu", command=retour_au_menu, bg='gray', fg='white')

charger_info()
cef.Initialize()
window.mainloop()
cef.Shutdown()
