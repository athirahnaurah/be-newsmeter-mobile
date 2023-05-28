token = None  # Inisialisasi variabel global

def set_token(value):
    global token  # Deklarasikan variabel global di dalam fungsi
    token = value

def use_token():
    global token  # Deklarasikan variabel global di dalam fungsi
    if token is not None:
        return token
    else:
        print("token belum diatur.")
