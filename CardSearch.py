import requests
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from io import BytesIO
import webbrowser
from urllib.parse import quote
import re
import json


# pega as taxas de conversão (dolar e euro para reais)
def pegar_taxas():
    try:
        url = "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL"
        resposta = requests.get(url)
        dados = resposta.json()
        usd_brl = float(dados["USDBRL"]["bid"])
        eur_brl = float(dados["EURBRL"]["bid"])
        return {"USD": usd_brl, "EUR": eur_brl}
    except Exception as e:
        print("Erro ao buscar taxas:", e)
        return {"USD": None, "EUR": None}


taxas = pegar_taxas()


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import re

def pegar_preco_ligamagic(nome_carta_url):
    """ISSO SEMPRE VAI RODAR EM SEGUNDO PLANO TOME CUIDADO PQ LAGA DEMAIS A GENTE TEM QUE POR NO WEB BROWSER"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,1000")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/115.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        url = f"https://www.ligamagic.com.br/?view=cards/card&card={nome_carta_url}"
        driver.get(url)


        wait = WebDriverWait(driver, 10)
        try:

            elems = wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".bl-price.price-absolute-right")
                )
            )
        except TimeoutException:
            elems = driver.find_elements(By.XPATH, "//*[contains(text(), 'R$')]")

        price_texts = []
        for el in elems:
            txt = el.text.strip()
            m = re.search(r'R\$\s*[\d\.,]+', txt)
            if m:
                price_texts.append(m.group(0))

        if not price_texts:
            return "Não encontrado"


        def parse_price(txt):
            s = txt.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(s)
            except:
                return None

        parsed = [(txt, parse_price(txt)) for txt in price_texts if parse_price(txt)]
        if not parsed:
            return "Não encontrado"

        menor = min(parsed, key=lambda x: x[1])[1]
        return f"R$ {menor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception as e:
        print("Erro Ligamagic:", e)
        return "Erro"
    finally:
        driver.quit()




class ElementoVisual:
    def __init__(self, nome):
        self.nome = nome

    def exibir(self, parent):
        raise NotImplementedError("Erro (subclasses devem implementar exibir)")


class Carta(ElementoVisual):
    def __init__(self, nome, tipo, descricao, imagem_url, links_compra, precos):
        super().__init__(nome)
        self.tipo = tipo
        self.descricao = descricao
        self.imagem_url = imagem_url
        self.links_compra = links_compra
        self.precos = precos or {}

    def exibir(self, parent, linha, coluna):
        resposta_imagem = requests.get(self.imagem_url)
        img_dados = Image.open(BytesIO(resposta_imagem.content)).resize((200, 280))
        img = ImageTk.PhotoImage(img_dados)

        img_label = tk.Label(parent, image=img, bg="white")
        img_label.image = img
        img_label.grid(row=linha, column=coluna, padx=10, pady=10)
        img_label.bind("<Button-1>", lambda event: self.mostrar_detalhes())

    def mostrar_detalhes(self):
        janela_detalhes = tk.Toplevel(janela_principal)
        janela_detalhes.title(self.nome)

        resposta_imagem = requests.get(self.imagem_url)
        img_dados = Image.open(BytesIO(resposta_imagem.content)).resize((250, 350))
        img = ImageTk.PhotoImage(img_dados)

        img_label = tk.Label(janela_detalhes, image=img)
        img_label.image = img
        img_label.pack(padx=10, pady=10)

        detalhes = f"Nome: {self.nome}\nTipo: {self.tipo}\nDescrição: {self.descricao}"
        tk.Label(janela_detalhes, text=detalhes, justify="left").pack(padx=10, pady=10)

        # preços
        precos_txt = "Preços:\n"

        usd = self.precos.get("usd")
        usd_foil = self.precos.get("usd_foil")
        eur = self.precos.get("eur")
        tix = self.precos.get("tix")

        if usd:
            usd_valor = float(usd)
            brl = f" (R$ {usd_valor * taxas['USD']:.2f})" if taxas["USD"] else ""
            precos_txt += f"- USD: ${usd}{brl}\n"
        else:
            precos_txt += "- USD: Not available\n"

        if usd_foil:
            usd_foil_valor = float(usd_foil)
            brl = f" (R$ {usd_foil_valor * taxas['USD']:.2f})" if taxas["USD"] else ""
            precos_txt += f"- USD Foil: ${usd_foil}{brl}\n"
        else:
            precos_txt += "- USD Foil: Não tem\n"

        if eur:
            eur_valor = float(eur)
            brl = f" (R$ {eur_valor * taxas['EUR']:.2f})" if taxas["EUR"] else ""
            precos_txt += f"- EUR: €{eur}{brl}\n"
        else:
            precos_txt += "- EUR: Não tem\n"

        precos_txt += f"- MTGO Tix: {tix if tix else 'Não tem'}\n"

      #ligamagic aqui preço
        nome_carta_url = quote(self.nome)
        preco_liga = pegar_preco_ligamagic(nome_carta_url)
        precos_txt += f"\n- Ligamagic (Menor Preço): {preco_liga}\n"

        tk.Label(janela_detalhes, text=precos_txt, justify="left", fg="darkgreen").pack(padx=10, pady=5)

        if self.links_compra:
            tk.Label(janela_detalhes, text="Onde Comprar:", font=("Arial", 10, "bold")).pack(pady=5)
            for site, url in self.links_compra.items():
                tk.Button(
                    janela_detalhes, text=f"Comprar no {site.capitalize()}",
                    fg="blue", cursor="hand2",
                    command=lambda url=url: abrir_link(url)
                ).pack(anchor="w", padx=5, pady=2)

        nome_carta_url = quote(self.nome)
        url_ligamagic = f"https://www.ligamagic.com.br/?view=cards/card&card={nome_carta_url}"
        tk.Button(
            janela_detalhes, text="Buscar na Ligamagic",
            fg="blue", cursor="hand2",
            command=lambda: abrir_link(url_ligamagic)
        ).pack(anchor="w", padx=5, pady=2)


def abrir_link(url):
    webbrowser.open(url)


def buscar_cartas(direcao_pagina=0):
    global pagina_atual
    pagina_atual += direcao_pagina

    termo_busca = entrada_nome_carta.get()
    filtro_cor = cor_selecionada.get()
    cartas_por_pagina = entrada_cartas_por_pagina.get()

    try:
        cartas_por_pagina = int(cartas_por_pagina)
        if cartas_por_pagina > 8:
            raise ValueError("O limite máximo é 8 cartas por página.")
    except ValueError as e:
        messagebox.showerror("Entrada Inválida", str(e))
        return

    consulta = f'name:"{termo_busca}"'
    if filtro_cor != "nenhum":
        consulta += f'+color:"{filtro_cor}"'
    consulta += f"&page={pagina_atual}&per_page={cartas_por_pagina}"

    url = f"https://api.scryfall.com/cards/search?q={consulta}"
    try:
        resposta = requests.get(url)
        if resposta.status_code != 200:
            raise Exception(f"Erro ao consultar a API: {resposta.status_code}")

        dados = resposta.json()
        if not dados.get("data"):
            messagebox.showinfo("Sem Resultados", "Nenhuma carta encontrada na busca.")
            pagina_atual -= direcao_pagina
            return

        for widget in frame_imagens.winfo_children():
            widget.destroy()

        linha = 0
        coluna = 0
        for carta_dados in dados["data"]:
            if 'image_uris' in carta_dados:
                carta = Carta(
                    nome=carta_dados['name'],
                    tipo=carta_dados['type_line'],
                    descricao=carta_dados.get('oracle_text', 'Descrição não disponível.'),
                    imagem_url=carta_dados['image_uris']['normal'],
                    links_compra=carta_dados.get('purchase_uris', {}),
                    precos=carta_dados.get('prices', {})
                )
                carta.exibir(frame_imagens, linha, coluna)

                coluna += 1
                if coluna >= 4:
                    coluna = 0
                    linha += 1

        canvas.configure(scrollregion=canvas.bbox("all"))
    except Exception as e:
        messagebox.showerror("Erro", str(e))
        pagina_atual -= direcao_pagina


# config da interface N MUDE WALTER DA ULTIMA VEZ DEU PROBLEMA
janela_principal = tk.Tk()
janela_principal.title("Busca de Cartas Scryfall")
janela_principal.geometry("1280x720")

tk.Label(janela_principal, text="Nome da Carta:").grid(row=0, column=0, sticky="w", padx=10)
entrada_nome_carta = tk.Entry(janela_principal, width=30)
entrada_nome_carta.grid(row=0, column=1, padx=5, pady=5)

tk.Label(janela_principal, text="Filtro de Cor:").grid(row=1, column=0, sticky="w", padx=10)
cor_selecionada = tk.StringVar(value="nenhum")
for i, cor in enumerate(["nenhum", "vermelho", "azul", "branco", "verde", "preto"]):
    tk.Radiobutton(janela_principal, text=cor.capitalize(), variable=cor_selecionada, value=cor).grid(row=1,
                                                                                                      column=1 + i,
                                                                                                      sticky="w")

tk.Label(janela_principal, text="Cartas por Página:").grid(row=2, column=0, sticky="w", padx=10)
entrada_cartas_por_pagina = tk.Entry(janela_principal, width=5)
entrada_cartas_por_pagina.grid(row=2, column=1, padx=5, pady=5)
entrada_cartas_por_pagina.insert(0, "8")

pagina_atual = 1
frame_paginacao = tk.Frame(janela_principal)
frame_paginacao.grid(row=3, column=0, columnspan=6)

tk.Button(frame_paginacao, text="Página Anterior", command=lambda: buscar_cartas(-1)).grid(row=0, column=0, padx=5,
                                                                                           pady=5)
tk.Button(frame_paginacao, text="Buscar", command=lambda: buscar_cartas(0)).grid(row=0, column=1, padx=5, pady=5)
tk.Button(frame_paginacao, text="Próxima Página", command=lambda: buscar_cartas(1)).grid(row=0, column=2, padx=5,
                                                                                         pady=5)

canvas = tk.Canvas(janela_principal, width=1000, height=600)
scroll_y = tk.Scrollbar(janela_principal, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scroll_y.set)
canvas.grid(row=4, column=0, columnspan=6, pady=10, sticky="nsew")
scroll_y.grid(row=4, column=6, sticky="ns")

frame_imagens = tk.Frame(canvas)
canvas.create_window((0, 0), window=frame_imagens, anchor="nw")
frame_imagens.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))

canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

janela_principal.mainloop()


