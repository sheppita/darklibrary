import os
import re
import unicodedata
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
import requests
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ─────────────────────────────────────────────
# Configuração do banco de dados
# ─────────────────────────────────────────────

database_url = os.environ.get("DATABASE_URL", "")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)

# ─────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────

CORES_ORDEM = [
    "Branco", "Verde", "Azul", "Rosa", "Marrom",
    "Vermelho", "Laranja", "Amarelo", "Cinza", "Preto", "Multi",
]
CORES_INDICE = {cor: i for i, cor in enumerate(CORES_ORDEM)}

CORES_HEX = {
    "Branco":   "#f0ede6",
    "Verde":    "#4a7c59",
    "Azul":     "#3d5a80",
    "Rosa":     "#d88ba6",
    "Marrom":   "#7a5c3e",
    "Vermelho": "#b33a3a",
    "Laranja":  "#d97736",
    "Amarelo":  "#e0b73c",
    "Cinza":    "#9a9a9a",
    "Preto":    "#2a2a2a",
    "Multi":    "#e8dfc9",
}

STATUS_ITEM = ["nao_tenho", "tenho_nao_li", "li"]

STATUS_ROTULO = {
    "nao_tenho":    "Não tenho",
    "tenho_nao_li": "Tenho, não li",
    "li":           "Li",
}

# ─────────────────────────────────────────────
# Países — lista canônica e apelidos
# ─────────────────────────────────────────────

PAISES_CANONICOS = {
    "AF": "Afeganistão", "ZA": "África do Sul", "AL": "Albânia", "DE": "Alemanha",
    "AD": "Andorra", "AO": "Angola", "AI": "Anguila", "AQ": "Antártida",
    "AG": "Antígua e Barbuda", "SA": "Arábia Saudita", "DZ": "Argélia",
    "AR": "Argentina", "AM": "Armênia", "AW": "Aruba", "AU": "Austrália",
    "AT": "Áustria", "AZ": "Azerbaijão", "BS": "Bahamas", "BH": "Bahrein",
    "BD": "Bangladesh", "BB": "Barbados", "BE": "Bélgica", "BZ": "Belize",
    "BJ": "Benin", "BM": "Bermudas", "BY": "Belarus", "BO": "Bolívia",
    "BA": "Bósnia e Herzegovina", "BW": "Botsuana", "BR": "Brasil",
    "BN": "Brunei", "BG": "Bulgária", "BF": "Burkina Faso", "BI": "Burundi",
    "BT": "Butão", "CV": "Cabo Verde", "CM": "Camarões", "KH": "Camboja",
    "CA": "Canadá", "QA": "Catar", "KZ": "Cazaquistão", "TD": "Chade",
    "CL": "Chile", "CN": "China", "CY": "Chipre", "SG": "Cingapura",
    "CO": "Colômbia", "KM": "Comores", "CG": "Congo",
    "CD": "Congo, República Democrática do", "KP": "Coreia do Norte",
    "KR": "Coreia do Sul", "CI": "Costa do Marfim", "CR": "Costa Rica",
    "HR": "Croácia", "CU": "Cuba", "CW": "Curaçao", "DK": "Dinamarca",
    "DJ": "Djibuti", "DM": "Dominica", "EG": "Egito", "SV": "El Salvador",
    "AE": "Emirados Árabes Unidos", "EC": "Equador", "ER": "Eritreia",
    "SK": "Eslováquia", "SI": "Eslovênia", "ES": "Espanha", "US": "EUA",
    "EE": "Estônia", "SZ": "Essuatíni", "ET": "Etiópia",
    "FK": "Falkland (Malvinas)", "FJ": "Fiji", "PH": "Filipinas",
    "FI": "Finlândia", "FR": "França", "GA": "Gabão", "GM": "Gâmbia",
    "GH": "Gana", "GE": "Geórgia", "GS": "Geórgia do Sul", "GI": "Gibraltar",
    "GD": "Granada", "GR": "Grécia", "GL": "Groenlândia", "GP": "Guadalupe",
    "GU": "Guam", "GT": "Guatemala", "GY": "Guiana", "GF": "Guiana Francesa",
    "GN": "Guiné", "GQ": "Guiné Equatorial", "GW": "Guiné-Bissau", "HT": "Haiti",
    "HN": "Honduras", "HK": "Hong Kong", "HU": "Hungria", "YE": "Iêmen",
    "IM": "Ilha de Man", "IN": "Índia", "ID": "Indonésia", "IR": "Irã",
    "IQ": "Iraque", "IE": "Irlanda", "IS": "Islândia", "IL": "Israel",
    "IT": "Itália", "JM": "Jamaica", "JP": "Japão", "JO": "Jordânia",
    "KI": "Kiribati", "KW": "Kuwait", "LA": "Laos", "LS": "Lesoto",
    "LV": "Letônia", "LB": "Líbano", "LR": "Libéria", "LY": "Líbia",
    "LI": "Liechtenstein", "LT": "Lituânia", "LU": "Luxemburgo", "MO": "Macau",
    "MK": "Macedônia do Norte", "MG": "Madagascar", "MY": "Malásia",
    "MW": "Malaui", "MV": "Maldivas", "ML": "Mali", "MT": "Malta",
    "MA": "Marrocos", "MQ": "Martinica", "MU": "Maurício", "MR": "Mauritânia",
    "MX": "México", "MM": "Mianmar", "FM": "Micronésia", "MZ": "Moçambique",
    "MD": "Moldávia", "MC": "Mônaco", "MN": "Mongólia", "ME": "Montenegro",
    "NA": "Namíbia", "NR": "Nauru", "NP": "Nepal", "NI": "Nicarágua",
    "NE": "Níger", "NG": "Nigéria", "NO": "Noruega", "NC": "Nova Caledônia",
    "NZ": "Nova Zelândia", "OM": "Omã", "NL": "Países Baixos", "PW": "Palau",
    "PS": "Palestina", "PA": "Panamá", "PG": "Papua-Nova Guiné",
    "PK": "Paquistão", "PY": "Paraguai", "PE": "Peru",
    "PF": "Polinésia Francesa", "PL": "Polônia", "PR": "Porto Rico",
    "PT": "Portugal", "KE": "Quênia", "KG": "Quirguistão", "GB": "Reino Unido",
    "CF": "República Centro-Africana", "DO": "República Dominicana",
    "RO": "Romênia", "RW": "Ruanda", "RU": "Rússia", "EH": "Saara Ocidental",
    "WS": "Samoa", "SM": "San Marino", "LC": "Santa Lúcia",
    "KN": "São Cristóvão e Névis", "ST": "São Tomé e Príncipe",
    "VC": "São Vicente e Granadinas", "SN": "Senegal", "SL": "Serra Leoa",
    "RS": "Sérvia", "SC": "Seychelles", "SY": "Síria", "SO": "Somália",
    "LK": "Sri Lanka", "SD": "Sudão", "SS": "Sudão do Sul", "SE": "Suécia",
    "CH": "Suíça", "SR": "Suriname", "TJ": "Tadjiquistão", "TH": "Tailândia",
    "TW": "Taiwan", "TZ": "Tanzânia", "CZ": "Tchéquia", "TL": "Timor-Leste",
    "TG": "Togo", "TK": "Tokelau", "TO": "Tonga", "TT": "Trinidad e Tobago",
    "TN": "Tunísia", "TM": "Turcomenistão", "TR": "Turquia", "TV": "Tuvalu",
    "UA": "Ucrânia", "UG": "Uganda", "UY": "Uruguai", "UZ": "Uzbequistão",
    "VU": "Vanuatu", "VA": "Vaticano", "VE": "Venezuela", "VN": "Vietnã",
    "ZM": "Zâmbia", "ZW": "Zimbábue",
}

PAIS_APELIDO = {
    "brasil": "BR",
    "eua": "US", "estados unidos": "US", "estados unidos da america": "US",
    "usa": "US", "united states": "US", "united states of america": "US",
    "reino unido": "GB", "inglaterra": "GB", "escocia": "GB",
    "pais de gales": "GB", "irlanda do norte": "GB", "gra bretanha": "GB",
    "uk": "GB", "gb": "GB", "great britain": "GB", "united kingdom": "GB",
    "paises baixos": "NL", "holanda": "NL", "netherlands": "NL",
    "tchequia": "CZ", "republica tcheca": "CZ", "republica checa": "CZ",
    "czech republic": "CZ",
    "mianmar": "MM", "birmania": "MM", "myanmar": "MM",
    "suazilandia": "SZ", "swaziland": "SZ",
    "vietname": "VN", "vietnam": "VN",
    "coreia do sul": "KR", "coreia do norte": "KP",
    "russia": "RU", "federacao russa": "RU",
    "ira": "IR", "iran": "IR",
    "congo": "CG", "republica do congo": "CG", "congo brazzaville": "CG",
    "congo kinshasa": "CD", "republica democratica do congo": "CD", "rdc": "CD",
    "macedonia": "MK", "macedonia do norte": "MK", "north macedonia": "MK",
    "timor leste": "TL", "timor-leste": "TL", "east timor": "TL",
    "cabo verde": "CV", "cape verde": "CV",
    "guine bissau": "GW", "guine-bissau": "GW",
    "sao tome e principe": "ST",
    "antigua e barbuda": "AG",
    "trinidad e tobago": "TT",
    "sao cristovao e nevis": "KN",
    "sao vicente e granadinas": "VC",
    "belarus": "BY", "bielorrussia": "BY", "bielo-russia": "BY",
    "moldavia": "MD", "moldova": "MD",
}

# ─────────────────────────────────────────────
# Modelos
# ─────────────────────────────────────────────

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    pais = db.Column(db.String(80))
    cor_lombada = db.Column(db.String(20))
    estante = db.Column(db.String(20))
    isbn = db.Column(db.String(20))
    lido = db.Column(db.Boolean, default=False)
    capa_url = db.Column(db.String(500))
    literario = db.Column(db.Boolean, default=False)

    # ── Campos novos da Etapa 20 (Reforma) ──
    tenho = db.Column(db.Boolean, default=True, nullable=False)
    projeto_nobel = db.Column(db.Boolean, default=False, nullable=False)
    projeto_mundo = db.Column(db.Boolean, default=False, nullable=False)
    projeto_postgrad = db.Column(db.Boolean, default=False, nullable=False)
    projeto_tbr = db.Column(db.Boolean, default=False, nullable=False)
    postgrad_subprojeto = db.Column(db.String(20))
    subtitulo = db.Column(db.String(200))
    ano = db.Column(db.Integer)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Livro {self.titulo}>"

class Projeto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    tipo = db.Column(db.String(40))
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    itens = db.relationship(
        "ItemProjeto",
        back_populates="projeto",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ItemProjeto.ordem, ItemProjeto.titulo",
    )

    def __repr__(self):
        return f"<Projeto {self.nome}>"

class ItemProjeto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    projeto_id = db.Column(
        db.Integer,
        db.ForeignKey("projeto.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    subtitulo = db.Column(db.String(200))
    pais = db.Column(db.String(80), index=True)
    pais_codigo = db.Column(db.String(2), index=True)
    ano = db.Column(db.Integer)
    isbn = db.Column(db.String(20))
    capa_url = db.Column(db.String(500))
    observacoes = db.Column(db.Text)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="nao_tenho",
        index=True,
    )

    livro_id = db.Column(
        db.Integer,
        db.ForeignKey("livro.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ordem = db.Column(db.Integer)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    projeto = db.relationship("Projeto", back_populates="itens")
    livro = db.relationship("Livro")

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('nao_tenho','tenho_nao_li','li')",
            name="status_valido",
        ),
    )

    def __repr__(self):
        return f"<ItemProjeto {self.titulo} ({self.status})>"

# ─────────────────────────────────────────────
# Funções auxiliares
# ─────────────────────────────────────────────

def chave_ordenacao(livro):
    estante = (livro.estante or "").strip().upper()
    if not estante:
        grupo_estante = (1, "", 0)
    else:
        m = re.fullmatch(r"([A-Z]+)(\d+)", estante)
        if m:
            grupo_estante = (0, m.group(1), int(m.group(2)))
        else:
            grupo_estante = (1, estante, 0)

    cor = (livro.cor_lombada or "").strip()
    ordem_cor = CORES_INDICE.get(cor, CORES_INDICE["Multi"])
    titulo = (livro.titulo or "").lower()
    return (grupo_estante, ordem_cor, titulo)

def chave_ordenacao_estante_simples(estante):
    estante = (estante or "").strip().upper()
    m = re.fullmatch(r"([A-Z]+)(\d+)", estante)
    if m:
        return (0, m.group(1), int(m.group(2)))
    return (1, estante, 0)

def chave_ordenacao_item(item):
    ano = item.ano if item.ano is not None else 0
    return (-ano, (item.titulo or "").lower())

def sql_escape(valor):
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    texto = str(valor).replace("'", "''")
    return f"'{texto}'"

def limpar_texto(s):
    if s is None:
        return None
    s = s.strip()
    return s if s else None

def normalizar_isbn(isbn):
    if not isbn:
        return None
    limpo = re.sub(r"[^0-9Xx]", "", isbn)
    return limpo or None

def normalizar_texto(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def chave_livro(livro):
    return (
        normalizar_isbn(livro.isbn),
        normalizar_texto(livro.titulo),
        normalizar_texto(livro.autor),
    )

def chave_item(item):
    return (
        normalizar_isbn(item.isbn),
        normalizar_texto(item.titulo),
        normalizar_texto(item.autor),
    )

def _extrair_campos_item_do_form():
    status = request.form.get("status", "").strip()
    if status not in STATUS_ITEM:
        status = "nao_tenho"

    ano_raw = request.form.get("ano", "").strip()
    ano = None
    if ano_raw:
        try:
            ano = int(ano_raw)
        except ValueError:
            ano = None

    isbn = limpar_texto(request.form.get("isbn"))
    capa_url = limpar_texto(request.form.get("capa_url"))

    if not capa_url and isbn:
        capa_url = url_capa_open_library(isbn)

    pais_texto = limpar_texto(request.form.get("pais"))
    pais_codigo = codigo_pais_do_texto(pais_texto) if pais_texto else None

    return {
        "titulo": (request.form.get("titulo", "") or "").strip(),
        "autor": (request.form.get("autor", "") or "").strip(),
        "subtitulo": limpar_texto(request.form.get("subtitulo")),
        "pais": pais_texto,
        "pais_codigo": pais_codigo,
        "ano": ano,
        "isbn": isbn,
        "capa_url": capa_url,
        "observacoes": limpar_texto(request.form.get("observacoes")),
        "status": status,
    }

# ─────────────────────────────────────────────
# Funções de vinculação e sincronização
# ─────────────────────────────────────────────

def _livros_em_memoria():
    livros = Livro.query.all()
    return [(chave_livro(lv), lv) for lv in livros]

def encontrar_livro_para_item(item, livros_chaves):
    isbn_item, titulo_item, autor_item = chave_item(item)

    if isbn_item:
        for chave, lv in livros_chaves:
            if chave[0] == isbn_item:
                return lv

    if titulo_item and autor_item:
        for chave, lv in livros_chaves:
            if chave[1] == titulo_item and chave[2] == autor_item:
                return lv

    return None

def sincronizar_item_com_livro(item):
    if item.livro is None:
        return
    if item.livro.lido:
        item.status = "li"
    else:
        item.status = "tenho_nao_li"

def vincular_item_a_livro(item, livro):
    item.livro_id = livro.id
    item.livro = livro
    sincronizar_item_com_livro(item)

def tentar_vincular_item(item):
    if item.livro_id is not None:
        sincronizar_item_com_livro(item)
        return False

    livros_chaves = _livros_em_memoria()
    livro = encontrar_livro_para_item(item, livros_chaves)
    if livro is None:
        return False

    vincular_item_a_livro(item, livro)
    return True

def tentar_vincular_livro(livro):
    chave_lv = chave_livro(livro)

    itens = ItemProjeto.query.filter(ItemProjeto.livro_id.is_(None)).all()

    vinculados = 0
    for item in itens:
        chave_it = chave_item(item)
        bate = False
        if chave_lv[0] and chave_it[0] and chave_lv[0] == chave_it[0]:
            bate = True
        elif chave_lv[1] and chave_it[1] and chave_lv[2] and chave_it[2] \
                and chave_lv[1] == chave_it[1] and chave_lv[2] == chave_it[2]:
            bate = True

        if bate:
            vincular_item_a_livro(item, livro)
            vinculados += 1

    return vinculados

def sincronizar_itens_do_livro(livro):
    itens = ItemProjeto.query.filter(ItemProjeto.livro_id == livro.id).all()
    afetados = 0
    for item in itens:
        antes = item.status
        sincronizar_item_com_livro(item)
        if item.status != antes:
            afetados += 1
    return afetados

def preparar_exclusao_de_livro(livro):
    itens = ItemProjeto.query.filter(ItemProjeto.livro_id == livro.id).all()
    for item in itens:
        if item.status == "tenho_nao_li":
            item.status = "nao_tenho"
        item.livro_id = None

# ─────────────────────────────────────────────
# Funções de país e mapa
# ─────────────────────────────────────────────

_PAIS_CANONICO_NORMALIZADO_CACHE = None

def _obter_mapa_canonico_normalizado():
    global _PAIS_CANONICO_NORMALIZADO_CACHE
    if _PAIS_CANONICO_NORMALIZADO_CACHE is None:
        _PAIS_CANONICO_NORMALIZADO_CACHE = {
            normalizar_texto(nome): codigo
            for codigo, nome in PAISES_CANONICOS.items()
        }
    return _PAIS_CANONICO_NORMALIZADO_CACHE

def codigo_pais_do_texto(texto):
    if not texto:
        return None
    chave = normalizar_texto(texto)
    if not chave:
        return None

    if chave in PAIS_APELIDO:
        return PAIS_APELIDO[chave]

    canonico = _obter_mapa_canonico_normalizado()
    if chave in canonico:
        return canonico[chave]

    codigo_upper = (texto or "").strip().upper()
    if codigo_upper in PAISES_CANONICOS:
        return codigo_upper

    return None

def montar_dados_do_mapa(projeto):
    """
    Monta os dados do mapa para o projeto tipo 'mundo'.
    Considera APENAS itens do projeto com status='li'.
    """
    dados = {}
    nao_reconhecidos = {}

    def adicionar(codigo, nome, titulo, autor, capa_url):
        if codigo not in dados:
            dados[codigo] = {"nome": nome, "livros": [], "total": 0}
        dados[codigo]["livros"].append({
            "titulo": titulo or "(sem título)",
            "autor": autor or "",
            "origem": "projeto",
            "capa_url": capa_url or "",
        })
        dados[codigo]["total"] += 1

    itens_lidos = ItemProjeto.query.filter(
        ItemProjeto.projeto_id == projeto.id,
        ItemProjeto.status == "li",
    ).all()

    for it in itens_lidos:
        codigo = it.pais_codigo or codigo_pais_do_texto(it.pais)
        if codigo:
            adicionar(codigo, PAISES_CANONICOS[codigo], it.titulo, it.autor, it.capa_url)
        else:
            chave = (it.pais or "").strip() or "(sem país)"
            nao_reconhecidos.setdefault(chave, []).append({
                "titulo": it.titulo or "(sem título)",
                "autor": it.autor or "",
                "origem": "projeto",
            })

    return dados, nao_reconhecidos

def resumo_do_mapa(dados_mapa):
    paises_lidos = len(dados_mapa)
    total_paises = len(PAISES_CANONICOS)
    return {
        "paises_lidos": paises_lidos,
        "total_paises": total_paises,
    }

def _montar_livros_lidos_do_projeto(dados_mapa):
    """
    Monta a lista de livros lidos do projeto tipo 'mundo',
    a partir do dicionário montado por montar_dados_do_mapa().
    """
    if not dados_mapa:
        return []

    livros = []
    for codigo, info in dados_mapa.items():
        nome_pais = info.get("nome", codigo)
        for livro in info.get("livros", []):
            livros.append({
                "titulo": livro.get("titulo", ""),
                "autor": livro.get("autor", ""),
                "pais": nome_pais,
                "origem": livro.get("origem", ""),
                "capa_url": livro.get("capa_url", ""),
            })

    livros.sort(key=lambda lv: (lv["pais"].lower(), lv["titulo"].lower()))
    return livros

def _conjunto_paises_lidos(projeto):
    """
    Retorna o conjunto de códigos ISO-2 de países com pelo menos um
    item do projeto Lendo o Mundo com status='li'.
    """
    codigos = set()
    itens = ItemProjeto.query.filter(
        ItemProjeto.projeto_id == projeto.id,
        ItemProjeto.status == "li",
    ).all()
    for it in itens:
        codigo = it.pais_codigo or codigo_pais_do_texto(it.pais)
        if codigo:
            codigos.add(codigo)
    return codigos

def _conjunto_paises_com_recomendacoes(projeto):
    codigos = set()
    itens = ItemProjeto.query.filter(ItemProjeto.projeto_id == projeto.id).all()
    for it in itens:
        codigo = it.pais_codigo or codigo_pais_do_texto(it.pais)
        if codigo:
            codigos.add(codigo)
    return codigos

def listar_paises_do_projeto(projeto, filtro):
    lidos = _conjunto_paises_lidos(projeto)
    com_rec = _conjunto_paises_com_recomendacoes(projeto)

    itens_projeto = ItemProjeto.query.filter(
        ItemProjeto.projeto_id == projeto.id
    ).all()

    contagem_rec = {}
    for it in itens_projeto:
        codigo = it.pais_codigo or codigo_pais_do_texto(it.pais)
        if codigo:
            contagem_rec[codigo] = contagem_rec.get(codigo, 0) + 1

    lista = []
    for codigo in sorted(
        PAISES_CANONICOS.keys(),
        key=lambda c: normalizar_texto(PAISES_CANONICOS[c]),
    ):
        lista.append({
            "codigo": codigo,
            "nome": PAISES_CANONICOS[codigo],
            "lido": codigo in lidos,
            "com_recomendacoes": codigo in com_rec,
            "qtd_recomendacoes": contagem_rec.get(codigo, 0),
        })

    if filtro == "lidos":
        lista = [p for p in lista if p["lido"]]
    elif filtro == "nao_lidos":
        lista = [p for p in lista if not p["lido"]]
    elif filtro == "com_recomendacoes":
        lista = [p for p in lista if p["com_recomendacoes"]]

    return lista

def listar_recomendacoes_do_pais(projeto, codigo):
    itens = ItemProjeto.query.filter(ItemProjeto.projeto_id == projeto.id).all()
    resultado = [
        it for it in itens
        if (it.pais_codigo or codigo_pais_do_texto(it.pais)) == codigo
    ]
    resultado.sort(key=chave_ordenacao_item)
    return resultado

def listar_livros_lidos_do_pais(projeto, codigo):
    """
    Retorna itens do projeto Lendo o Mundo com status='li' para o país.
    Apenas itens do projeto são considerados (não mais livros da DL).
    """
    itens = ItemProjeto.query.filter(
        ItemProjeto.projeto_id == projeto.id,
        ItemProjeto.status == "li",
    ).all()

    itens_pais = [
        it for it in itens
        if (it.pais_codigo or codigo_pais_do_texto(it.pais)) == codigo
    ]

    return itens_pais

# ─────────────────────────────────────────────
# Busca de ISBN
# ─────────────────────────────────────────────

def url_capa_open_library(isbn):
    if not isbn:
        return None
    isbn_limpo = re.sub(r"[^0-9Xx]", "", isbn)
    if not isbn_limpo:
        return None
    return f"https://covers.openlibrary.org/b/isbn/{isbn_limpo}-L.jpg?default=false"

def buscar_google_books(isbn_limpo):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_limpo}"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        dados = r.json()
    except requests.RequestException:
        return None

    items = dados.get("items", [])
    if not items:
        return None

    info = items[0].get("volumeInfo", {})
    titulo = info.get("title", "")
    autores = info.get("authors", [])
    autor = autores[0] if autores else ""

    capa = ""
    links = info.get("imageLinks", {})
    if links:
        capa = links.get("thumbnail") or links.get("smallThumbnail") or ""
        if capa:
            capa = capa.replace("http://", "https://", 1)
            capa = re.sub(r"&zoom=\d+", "", capa)

    return {"titulo": titulo, "autor": autor, "capa": capa}

def buscar_open_library(isbn_limpo):
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn_limpo}&format=json&jscmd=data"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        dados = r.json()
    except requests.RequestException:
        return None

    chave = f"ISBN:{isbn_limpo}"
    if chave not in dados:
        return None

    info = dados[chave]
    titulo = info.get("title", "")
    autores = info.get("authors", [])
    autor = autores[0]["name"] if autores else ""

    capa = ""
    if "cover" in info and "medium" in info["cover"]:
        capa = info["cover"]["medium"]

    return {"titulo": titulo, "autor": autor, "capa": capa}

# ─────────────────────────────────────────────
# Utilidade: validação de next
# ─────────────────────────────────────────────

def url_next_valida(url):
    if not url:
        return None
    url = url.strip()
    if not url.startswith("/"):
        return None
    if url.startswith("//"):
        return None
    return url

# ─────────────────────────────────────────────
# Rotas — livros
# ─────────────────────────────────────────────

@app.route("/")
def home():
    busca = request.args.get("q", "").strip()
    filtro_estante = request.args.get("estante", "").strip().upper()
    filtro_cor = request.args.get("cor", "").strip()
    filtro_status = request.args.get("status", "").strip()
    filtro_pais = request.args.get("pais", "").strip()

    query = Livro.query

    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            db.or_(
                Livro.titulo.ilike(termo),
                Livro.autor.ilike(termo),
            )
        )

    if filtro_estante:
        query = query.filter(Livro.estante == filtro_estante)

    if filtro_cor:
        query = query.filter(Livro.cor_lombada == filtro_cor)

    if filtro_pais:
        query = query.filter(Livro.pais == filtro_pais)

    if filtro_status == "lido":
        query = query.filter(Livro.lido.is_(True))
    elif filtro_status == "nao_lido":
        query = query.filter(Livro.lido.is_(False))

    livros = query.all()
    livros.sort(key=chave_ordenacao)

    for livro in livros:
        cor = (livro.cor_lombada or "").strip()
        livro.cor_hex = CORES_HEX.get(cor, CORES_HEX["Multi"])

        if livro.capa_url:
            livro.capa_final = livro.capa_url
        else:
            livro.capa_final = url_capa_open_library(livro.isbn)

    grupos = []
    estante_atual = "__inicio__"
    for livro in livros:
        if livro.estante != estante_atual:
            grupos.append((livro.estante, []))
            estante_atual = livro.estante
        grupos[-1][1].append(livro)

    grupos_com_gradiente = []
    for estante, livros_do_grupo in grupos:
        cores = [livro.cor_hex for livro in livros_do_grupo]

        if len(cores) == 1:
            gradiente = cores[0]
        else:
            passo = 100 / len(cores)
            stops = []
            for i, cor in enumerate(cores):
                inicio = i * passo
                fim = (i + 1) * passo
                stops.append(f"{cor} {inicio:.2f}% {fim:.2f}%")
            gradiente = f"linear-gradient(to right, {', '.join(stops)})"

        grupos_com_gradiente.append((estante, livros_do_grupo, gradiente))

    estantes_disponiveis = sorted(
        [e for (e,) in db.session.query(Livro.estante).distinct().all() if e],
        key=chave_ordenacao_estante_simples,
    )

    paises_disponiveis = sorted(
        [p for (p,) in db.session.query(Livro.pais).distinct().all() if p],
        key=lambda s: normalizar_texto(s),
    )

    args_atuais = request.args.to_dict(flat=True)
    next_url = request.path
    if args_atuais:
        from urllib.parse import urlencode
        next_url = f"{request.path}?{urlencode(args_atuais)}"

    return render_template(
        "lista.html",
        grupos=grupos_com_gradiente,
        total=len(livros),
        busca=busca,
        filtro_estante=filtro_estante,
        filtro_cor=filtro_cor,
        filtro_status=filtro_status,
        filtro_pais=filtro_pais,
        estantes=estantes_disponiveis,
        paises=paises_disponiveis,
        cores=CORES_ORDEM,
        next_url=next_url,
    )

@app.route("/novo", methods=["GET", "POST"])
def novo():
    item_id_raw = request.args.get("item_id") or request.form.get("item_id")
    item_origem = None
    if item_id_raw:
        try:
            item_origem = db.session.get(ItemProjeto, int(item_id_raw))
        except (ValueError, TypeError):
            item_origem = None

    next_url = url_next_valida(request.args.get("next") or request.form.get("next"))

    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip() or None
        capa_form = request.form.get("capa_url", "").strip() or None

        livro = Livro(
            titulo=request.form.get("titulo", "").strip(),
            autor=request.form.get("autor", "").strip(),
            pais=request.form.get("pais", "").strip() or None,
            cor_lombada=request.form.get("cor_lombada", "").strip() or None,
            estante=request.form.get("estante", "").strip().upper() or None,
            isbn=isbn,
            lido=("lido" in request.form),
            capa_url=capa_form or url_capa_open_library(isbn),
            literario=("literario" in request.form),
        )
        db.session.add(livro)
        db.session.flush()

        if item_origem is not None:
            vincular_item_a_livro(item_origem, livro)
        else:
            tentar_vincular_livro(livro)

        db.session.commit()

        if item_origem is not None:
            return redirect(url_for("projeto_detalhe", projeto_id=item_origem.projeto_id))
        if next_url:
            return redirect(next_url)
        return redirect(url_for("home"))

    if item_origem is not None:
        valores = {
            "titulo": item_origem.titulo or "",
            "autor": item_origem.autor or "",
            "pais": item_origem.pais or "",
            "isbn": item_origem.isbn or "",
            "capa_url": item_origem.capa_url or "",
        }
    else:
        valores = {}

    return render_template(
        "novo.html",
        cores=CORES_ORDEM,
        valores=valores,
        item_origem=item_origem,
        next_url=next_url,
    )

@app.route("/editar/<int:livro_id>", methods=["GET", "POST"])
def editar(livro_id):
    livro = db.get_or_404(Livro, livro_id)

    next_url = url_next_valida(request.args.get("next") or request.form.get("next"))

    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip() or None
        capa_form = request.form.get("capa_url", "").strip() or None

        lido_antes = livro.lido

        livro.titulo = request.form.get("titulo", "").strip()
        livro.autor = request.form.get("autor", "").strip()
        livro.pais = request.form.get("pais", "").strip() or None
        livro.cor_lombada = request.form.get("cor_lombada", "").strip() or None
        livro.estante = request.form.get("estante", "").strip().upper() or None
        livro.isbn = isbn
        livro.lido = ("lido" in request.form)
        livro.capa_url = capa_form or url_capa_open_library(isbn)
        livro.literario = ("literario" in request.form)

        db.session.flush()

        if livro.lido != lido_antes:
            sincronizar_itens_do_livro(livro)

        tentar_vincular_livro(livro)

        db.session.commit()

        if next_url:
            return redirect(next_url)
        return redirect(url_for("home"))

    return render_template("editar.html", livro=livro, cores=CORES_ORDEM, next_url=next_url)

@app.route("/excluir/<int:livro_id>", methods=["GET", "POST"])
def excluir(livro_id):
    livro = db.get_or_404(Livro, livro_id)

    next_url = url_next_valida(request.args.get("next") or request.form.get("next"))

    if request.method == "POST":
        preparar_exclusao_de_livro(livro)
        db.session.delete(livro)
        db.session.commit()

        if next_url:
            return redirect(next_url)
        return redirect(url_for("home"))

    return render_template("excluir.html", livro=livro, next_url=next_url)

@app.route("/estatisticas")
def estatisticas():
    total = Livro.query.count()
    total_lidos = Livro.query.filter(Livro.lido.is_(True)).count()
    total_nao_lidos = total - total_lidos

    if total > 0:
        pct_lidos = round(total_lidos / total * 100)
    else:
        pct_lidos = 0

    total_literarios = Livro.query.filter(Livro.literario.is_(True)).count()
    total_nao_literarios = total - total_literarios

    total_autores_distintos = (
        db.session.query(db.func.count(db.func.distinct(Livro.autor))).scalar() or 0
    )
    total_paises_distintos = (
        db.session.query(db.func.count(db.func.distinct(Livro.pais))).scalar() or 0
    )

    por_estante_raw = (
        db.session.query(Livro.estante, db.func.count(Livro.id))
        .group_by(Livro.estante)
        .all()
    )
    por_estante = sorted(
        [(e, n) for (e, n) in por_estante_raw if e],
        key=lambda par: chave_ordenacao_estante_simples(par[0]),
    )
    sem_estante = sum(n for (e, n) in por_estante_raw if not e)
    if sem_estante > 0:
        por_estante.append((None, sem_estante))

    top_autores = (
        db.session.query(Livro.autor, db.func.count(Livro.id))
        .group_by(Livro.autor)
        .order_by(db.func.count(Livro.id).desc(), Livro.autor.asc())
        .all()
    )

    por_pais = (
        db.session.query(Livro.pais, db.func.count(Livro.id))
        .group_by(Livro.pais)
        .order_by(db.func.count(Livro.id).desc())
        .all()
    )

    por_cor_raw = dict(
        db.session.query(Livro.cor_lombada, db.func.count(Livro.id))
        .group_by(Livro.cor_lombada)
        .all()
    )
    por_cor = [(cor, por_cor_raw.get(cor, 0)) for cor in CORES_ORDEM]
    sem_cor = por_cor_raw.get(None, 0)

    return render_template(
        "estatisticas.html",
        total=total,
        total_lidos=total_lidos,
        total_nao_lidos=total_nao_lidos,
        pct_lidos=pct_lidos,
        total_literarios=total_literarios,
        total_nao_literarios=total_nao_literarios,
        total_autores_distintos=total_autores_distintos,
        total_paises_distintos=total_paises_distintos,
        por_estante=por_estante,
        top_autores=top_autores,
        por_pais=por_pais,
        por_cor=por_cor,
        sem_cor=sem_cor,
        cores_hex=CORES_HEX,
    )

@app.route("/backup")
def backup():
    livros = Livro.query.order_by(Livro.id).all()
    projetos = Projeto.query.order_by(Projeto.id).all()
    itens = ItemProjeto.query.order_by(ItemProjeto.id).all()

    agora = datetime.now()
    data_iso = agora.strftime("%Y-%m-%d %H:%M:%S")
    data_arquivo = agora.strftime("%Y%m%d-%H%M")

    linhas = []
    linhas.append("-- Dark Library — Backup")
    linhas.append(f"-- Gerado em: {data_iso}")
    linhas.append(f"-- Livros: {len(livros)}")
    linhas.append(f"-- Projetos: {len(projetos)}")
    linhas.append(f"-- Itens de projeto: {len(itens)}")
    linhas.append("")
    linhas.append("-- Restauração:")
    linhas.append("-- 1. Abra o SQL Editor do Neon.")
    linhas.append("-- 2. Cole este arquivo inteiro e execute de uma vez.")
    linhas.append("-- 3. ATENÇÃO: os DELETE abaixo APAGAM os dados atuais.")
    linhas.append("-- 4. Restaure as três tabelas juntas, na ordem em que")
    linhas.append("--    aparecem os INSERTs (livro -> projeto -> item_projeto).")
    linhas.append("-- 5. Os SELECT setval no final ajustam as sequences.")
    linhas.append("")
    linhas.append("-- Limpeza (ordem direta, do filho para o pai):")
    linhas.append("DELETE FROM item_projeto;")
    linhas.append("DELETE FROM projeto;")
    linhas.append("DELETE FROM livro;")
    linhas.append("")

    linhas.append("-- Livros")
    if not livros:
        linhas.append("-- (nenhum livro cadastrado)")
    else:
        for livro in livros:
            valores = ", ".join([
                str(livro.id),
                sql_escape(livro.titulo),
                sql_escape(livro.autor),
                sql_escape(livro.pais),
                sql_escape(livro.cor_lombada),
                sql_escape(livro.estante),
                sql_escape(livro.isbn),
                sql_escape(livro.lido),
                sql_escape(livro.capa_url),
                sql_escape(livro.literario),
            ])
            linhas.append(
                "INSERT INTO livro (id, titulo, autor, pais, cor_lombada, estante, isbn, lido, capa_url, literario) "
                f"VALUES ({valores});"
            )
    linhas.append("")

    linhas.append("-- Projetos")
    if not projetos:
        linhas.append("-- (nenhum projeto cadastrado)")
    else:
        for p in projetos:
            valores = ", ".join([
                str(p.id),
                sql_escape(p.nome),
                sql_escape(p.descricao),
                sql_escape(p.tipo),
                sql_escape(p.ativo),
                sql_escape(p.criado_em),
            ])
            linhas.append(
                "INSERT INTO projeto (id, nome, descricao, tipo, ativo, criado_em) "
                f"VALUES ({valores});"
            )
    linhas.append("")

    linhas.append("-- Itens de projeto")
    if not itens:
        linhas.append("-- (nenhum item cadastrado)")
    else:
        for it in itens:
            valores = ", ".join([
                str(it.id),
                str(it.projeto_id),
                sql_escape(it.titulo),
                sql_escape(it.autor),
                sql_escape(it.subtitulo),
                sql_escape(it.pais),
                sql_escape(it.pais_codigo),
                sql_escape(it.ano),
                sql_escape(it.isbn),
                sql_escape(it.capa_url),
                sql_escape(it.observacoes),
                sql_escape(it.status),
                sql_escape(it.livro_id),
                sql_escape(it.ordem),
                sql_escape(it.criado_em),
            ])
            linhas.append(
                "INSERT INTO item_projeto "
                "(id, projeto_id, titulo, autor, subtitulo, pais, pais_codigo, ano, isbn, capa_url, observacoes, status, livro_id, ordem, criado_em) "
                f"VALUES ({valores});"
            )
    linhas.append("")

    linhas.append("-- Ajuste das sequences (próximo id após restauração)")
    linhas.append(
        "SELECT setval(pg_get_serial_sequence('livro', 'id'), "
        "COALESCE((SELECT MAX(id) FROM livro), 0) + 1, false);"
    )
    linhas.append(
        "SELECT setval(pg_get_serial_sequence('projeto', 'id'), "
        "COALESCE((SELECT MAX(id) FROM projeto), 0) + 1, false);"
    )
    linhas.append(
        "SELECT setval(pg_get_serial_sequence('item_projeto', 'id'), "
        "COALESCE((SELECT MAX(id) FROM item_projeto), 0) + 1, false);"
    )
    linhas.append("")

    conteudo = "\n".join(linhas)
    nome_arquivo = f"darklibrary-backup-{data_arquivo}.sql"

    return Response(
        conteudo,
        mimetype="application/sql",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"',
        },
    )

@app.route("/api/buscar_isbn/<isbn>")
def buscar_isbn(isbn):
    isbn_limpo = re.sub(r"[^0-9Xx]", "", isbn)

    if not isbn_limpo:
        return jsonify({"erro": "ISBN vazio"}), 400

    resultado = buscar_google_books(isbn_limpo)
    fonte = "Google Books"

    if not resultado:
        resultado = buscar_open_library(isbn_limpo)
        fonte = "Open Library"

    if not resultado:
        return jsonify({"erro": "ISBN não encontrado no Google Books nem na Open Library"}), 404

    titulo = resultado.get("titulo", "")
    autor = resultado.get("autor", "")
    capa = resultado.get("capa", "")

    if not capa:
        capa = url_capa_open_library(isbn_limpo)

    return jsonify({
        "isbn": isbn_limpo,
        "titulo": titulo,
        "autor": autor,
        "capa": capa,
        "fonte": fonte,
    })

# ─────────────────────────────────────────────
# Rotas — projetos
# ─────────────────────────────────────────────

@app.route("/projetos")
def projetos():
    lista = Projeto.query.filter(Projeto.ativo.is_(True)).order_by(Projeto.nome).all()

    projetos_com_contagem = []
    for p in lista:
        if p.tipo == "mundo":
            # Cobertura de países para projetos tipo 'mundo'
            dados_mapa, _ = montar_dados_do_mapa(p)
            resumo = resumo_do_mapa(dados_mapa)
            total = resumo["total_paises"]
            lidos = resumo["paises_lidos"]
        else:
            total = len(p.itens)
            lidos = sum(1 for it in p.itens if it.status == "li")

        pct = round(lidos / total * 100) if total > 0 else 0
        projetos_com_contagem.append({
            "projeto": p,
            "total": total,
            "lidos": lidos,
            "pct": pct,
            "tipo_mundo": p.tipo == "mundo",
        })

    return render_template("projetos.html", projetos=projetos_com_contagem)

@app.route("/projetos/<int:projeto_id>")
def projeto_detalhe(projeto_id):
    projeto = db.get_or_404(Projeto, projeto_id)

    itens = sorted(projeto.itens, key=chave_ordenacao_item)

    # Filtros em cápsula (só para projetos que NÃO são tipo 'mundo')
    filtro = request.args.get("filtro", "lido").strip()
    if filtro not in ("lido", "nao_lido", "tenho", "recomendacoes", "todos"):
        filtro = "lido"

    if projeto.tipo != "mundo":
        if filtro == "lido":
            itens = [it for it in itens if it.status == "li"]
        elif filtro == "nao_lido":
            itens = [it for it in itens if it.status != "li"]
        elif filtro == "tenho":
            itens = [it for it in itens if it.status == "tenho_nao_li"]
        elif filtro == "recomendacoes":
            itens = [it for it in itens if it.status == "nao_tenho"]
        # filtro == "todos": não filtra

    # Contagens do resumo SEMPRE refletem o total do projeto
    total = len(projeto.itens)
    lidos = sum(1 for it in projeto.itens if it.status == "li")
    tenho_nao_li = sum(1 for it in projeto.itens if it.status == "tenho_nao_li")
    nao_tenho = sum(1 for it in projeto.itens if it.status == "nao_tenho")

    pct = round(lidos / total * 100) if total > 0 else 0

    vinculados_msg = request.args.get("vinculados")
    if vinculados_msg is not None:
        try:
            vinculados_msg = int(vinculados_msg)
        except ValueError:
            vinculados_msg = None

    dados_mapa = None
    paises_nao_reconhecidos = None
    resumo_mapa = None
    livros_lidos_projeto = None

    if projeto.tipo == "mundo":
        dados_mapa, paises_nao_reconhecidos = montar_dados_do_mapa(projeto)
        resumo_mapa = resumo_do_mapa(dados_mapa)
        livros_lidos_projeto = _montar_livros_lidos_do_projeto(dados_mapa)

    return render_template(
        "projeto.html",
        projeto=projeto,
        itens=itens,
        total=total,
        lidos=lidos,
        tenho_nao_li=tenho_nao_li,
        nao_tenho=nao_tenho,
        pct=pct,
        status_rotulo=STATUS_ROTULO,
        vinculados_msg=vinculados_msg,
        dados_mapa=dados_mapa,
        paises_nao_reconhecidos=paises_nao_reconhecidos,
        resumo_mapa=resumo_mapa,
        livros_lidos_projeto=livros_lidos_projeto,
        filtro=filtro,
    )

@app.route("/projetos/<int:projeto_id>/paises")
def projeto_paises(projeto_id):
    projeto = db.get_or_404(Projeto, projeto_id)

    filtro = request.args.get("filtro", "lidos").strip()
    if filtro not in ("lidos", "nao_lidos", "com_recomendacoes", "todos"):
        filtro = "lidos"

    paises = listar_paises_do_projeto(projeto, filtro)

    return render_template(
        "paises.html",
        projeto=projeto,
        paises=paises,
        filtro=filtro,
    )

@app.route("/projetos/<int:projeto_id>/paises/<codigo>")
def projeto_pais_detalhe(projeto_id, codigo):
    projeto = db.get_or_404(Projeto, projeto_id)

    codigo = (codigo or "").strip().upper()
    if codigo not in PAISES_CANONICOS:
        return f"País '{codigo}' não reconhecido.", 404

    nome = PAISES_CANONICOS[codigo]

    itens_lidos = listar_livros_lidos_do_pais(projeto, codigo)
    recomendacoes = listar_recomendacoes_do_pais(projeto, codigo)

    return render_template(
        "pais.html",
        projeto=projeto,
        codigo=codigo,
        nome=nome,
        livros_lidos=[],
        itens_lidos=itens_lidos,
        recomendacoes=recomendacoes,
        status_rotulo=STATUS_ROTULO,
    )

@app.route("/projetos/<int:projeto_id>/paises/<codigo>/recomendacoes/nova", methods=["GET", "POST"])
def recomendacao_nova(projeto_id, codigo):
    projeto = db.get_or_404(Projeto, projeto_id)

    codigo = (codigo or "").strip().upper()
    if codigo not in PAISES_CANONICOS:
        return f"País '{codigo}' não reconhecido.", 404

    nome = PAISES_CANONICOS[codigo]

    if request.method == "POST":
        dados = _extrair_campos_item_do_form()
        dados["pais"] = nome
        dados["pais_codigo"] = codigo

        if not dados["titulo"] or not dados["autor"]:
            return render_template(
                "item_novo.html",
                projeto=projeto,
                status_item=STATUS_ITEM,
                status_rotulo=STATUS_ROTULO,
                valores=dados,
                erro="Título e autor são obrigatórios.",
                pais_fixo={"codigo": codigo, "nome": nome},
            ), 400

        item = ItemProjeto(
            projeto_id=projeto.id,
            titulo=dados["titulo"],
            autor=dados["autor"],
            subtitulo=dados["subtitulo"],
            pais=nome,
            pais_codigo=codigo,
            ano=dados["ano"],
            isbn=dados["isbn"],
            capa_url=dados["capa_url"],
            observacoes=dados["observacoes"],
            status=dados["status"],
        )
        db.session.add(item)
        db.session.flush()
        tentar_vincular_item(item)
        db.session.commit()

        return redirect(url_for("projeto_pais_detalhe", projeto_id=projeto.id, codigo=codigo))

    return render_template(
        "item_novo.html",
        projeto=projeto,
        status_item=STATUS_ITEM,
        status_rotulo=STATUS_ROTULO,
        valores={},
        erro=None,
        pais_fixo={"codigo": codigo, "nome": nome},
    )

@app.route("/projetos/<int:projeto_id>/paises/<codigo>/recomendacoes/<int:item_id>/editar", methods=["GET", "POST"])
def recomendacao_editar(projeto_id, codigo, item_id):
    projeto = db.get_or_404(Projeto, projeto_id)
    item = db.get_or_404(ItemProjeto, item_id)

    codigo = (codigo or "").strip().upper()
    if codigo not in PAISES_CANONICOS:
        return f"País '{codigo}' não reconhecido.", 404

    if item.projeto_id != projeto.id:
        return "Este item não pertence a este projeto.", 404

    nome = PAISES_CANONICOS[codigo]

    if request.method == "POST":
        dados = _extrair_campos_item_do_form()
        dados["pais"] = nome
        dados["pais_codigo"] = codigo

        if not dados["titulo"] or not dados["autor"]:
            return render_template(
                "item_editar.html",
                projeto=projeto,
                item=item,
                status_item=STATUS_ITEM,
                status_rotulo=STATUS_ROTULO,
                erro="Título e autor são obrigatórios.",
                pais_fixo={"codigo": codigo, "nome": nome},
            ), 400

        item.titulo = dados["titulo"]
        item.autor = dados["autor"]
        item.subtitulo = dados["subtitulo"]
        item.pais = nome
        item.pais_codigo = codigo
        item.ano = dados["ano"]
        item.isbn = dados["isbn"]
        item.capa_url = dados["capa_url"]
        item.observacoes = dados["observacoes"]
        item.status = dados["status"]

        db.session.flush()
        tentar_vincular_item(item)
        db.session.commit()
        return redirect(url_for("projeto_pais_detalhe", projeto_id=projeto.id, codigo=codigo))

    return render_template(
        "item_editar.html",
        projeto=projeto,
        item=item,
        status_item=STATUS_ITEM,
        status_rotulo=STATUS_ROTULO,
        erro=None,
        pais_fixo={"codigo": codigo, "nome": nome},
    )

@app.route("/projetos/<int:projeto_id>/paises/<codigo>/recomendacoes/<int:item_id>/excluir", methods=["GET", "POST"])
def recomendacao_excluir(projeto_id, codigo, item_id):
    projeto = db.get_or_404(Projeto, projeto_id)
    item = db.get_or_404(ItemProjeto, item_id)

    codigo = (codigo or "").strip().upper()
    if codigo not in PAISES_CANONICOS:
        return f"País '{codigo}' não reconhecido.", 404

    if item.projeto_id != projeto.id:
        return "Este item não pertence a este projeto.", 404

    if request.method == "POST":
        db.session.delete(item)
        db.session.commit()
        return redirect(url_for("projeto_pais_detalhe", projeto_id=projeto.id, codigo=codigo))

    return render_template(
        "item_excluir.html",
        projeto=projeto,
        item=item,
        status_rotulo=STATUS_ROTULO,
    )

@app.route("/projetos/<int:projeto_id>/itens/novo", methods=["GET", "POST"])
def item_novo(projeto_id):
    projeto = db.get_or_404(Projeto, projeto_id)

    if request.method == "POST":
        dados = _extrair_campos_item_do_form()

        if not dados["titulo"] or not dados["autor"]:
            return render_template(
                "item_novo.html",
                projeto=projeto,
                status_item=STATUS_ITEM,
                status_rotulo=STATUS_ROTULO,
                valores=dados,
                erro="Título e autor são obrigatórios.",
                pais_fixo=None,
            ), 400

        item = ItemProjeto(
            projeto_id=projeto.id,
            titulo=dados["titulo"],
            autor=dados["autor"],
            subtitulo=dados["subtitulo"],
            pais=dados["pais"],
            pais_codigo=dados["pais_codigo"],
            ano=dados["ano"],
            isbn=dados["isbn"],
            capa_url=dados["capa_url"],
            observacoes=dados["observacoes"],
            status=dados["status"],
        )
        db.session.add(item)
        db.session.flush()

        tentar_vincular_item(item)

        db.session.commit()
        return redirect(url_for("projeto_detalhe", projeto_id=projeto.id))

    return render_template(
        "item_novo.html",
        projeto=projeto,
        status_item=STATUS_ITEM,
        status_rotulo=STATUS_ROTULO,
        valores={},
        erro=None,
        pais_fixo=None,
    )

@app.route("/projetos/<int:projeto_id>/itens/<int:item_id>/editar", methods=["GET", "POST"])
def item_editar(projeto_id, item_id):
    projeto = db.get_or_404(Projeto, projeto_id)
    item = db.get_or_404(ItemProjeto, item_id)

    if item.projeto_id != projeto.id:
        return "Este item não pertence a este projeto.", 404

    if request.method == "POST":
        dados = _extrair_campos_item_do_form()

        if not dados["titulo"] or not dados["autor"]:
            return render_template(
                "item_editar.html",
                projeto=projeto,
                item=item,
                status_item=STATUS_ITEM,
                status_rotulo=STATUS_ROTULO,
                erro="Título e autor são obrigatórios.",
                pais_fixo=None,
            ), 400

        item.titulo = dados["titulo"]
        item.autor = dados["autor"]
        item.subtitulo = dados["subtitulo"]
        item.pais = dados["pais"]
        item.pais_codigo = dados["pais_codigo"]
        item.ano = dados["ano"]
        item.isbn = dados["isbn"]
        item.capa_url = dados["capa_url"]
        item.observacoes = dados["observacoes"]
        item.status = dados["status"]

        db.session.flush()
        tentar_vincular_item(item)
        db.session.commit()
        return redirect(url_for("projeto_detalhe", projeto_id=projeto.id))

    return render_template(
        "item_editar.html",
        projeto=projeto,
        item=item,
        status_item=STATUS_ITEM,
        status_rotulo=STATUS_ROTULO,
        erro=None,
        pais_fixo=None,
    )

@app.route("/projetos/<int:projeto_id>/itens/<int:item_id>/excluir", methods=["GET", "POST"])
def item_excluir(projeto_id, item_id):
    projeto = db.get_or_404(Projeto, projeto_id)
    item = db.get_or_404(ItemProjeto, item_id)

    if item.projeto_id != projeto.id:
        return "Este item não pertence a este projeto.", 404

    if request.method == "POST":
        db.session.delete(item)
        db.session.commit()
        return redirect(url_for("projeto_detalhe", projeto_id=projeto.id))

    return render_template(
        "item_excluir.html",
        projeto=projeto,
        item=item,
        status_rotulo=STATUS_ROTULO,
    )

@app.route("/projetos/<int:projeto_id>/vincular_automaticamente", methods=["POST"])
def projeto_vincular_automaticamente(projeto_id):
    projeto = db.get_or_404(Projeto, projeto_id)

    livros_chaves = _livros_em_memoria()

    vinculados = 0
    for item in projeto.itens:
        if item.livro_id is not None:
            sincronizar_item_com_livro(item)
            continue

        livro = encontrar_livro_para_item(item, livros_chaves)
        if livro is not None:
            vincular_item_a_livro(item, livro)
            vinculados += 1

    db.session.commit()

    return redirect(url_for("projeto_detalhe", projeto_id=projeto.id, vinculados=vinculados))

@app.route("/projetos/<int:projeto_id>/excluir", methods=["GET", "POST"])
def projeto_excluir(projeto_id):
    projeto = db.get_or_404(Projeto, projeto_id)

    if request.method == "POST":
        # Apaga o projeto. Os itens vão junto (cascade).
        # Os livros da DL vinculados ficam intactos — a FK
        # ON DELETE SET NULL desvincula item_projeto.livro_id.
        db.session.delete(projeto)
        db.session.commit()
        return redirect(url_for("projetos"))

    return render_template("projeto_excluir.html", projeto=projeto)

# ─────────────────────────────────────────────
# Criação automática das tabelas
# ─────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
