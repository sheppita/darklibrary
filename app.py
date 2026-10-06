import os
import re
import unicodedata
from datetime import datetime, UTC
from urllib.parse import urlencode
from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ─────────────────────────────────────────────
# Configuração do banco de dados
# ─────────────────────────────────────────────

database_url = os.environ.get("DATABASE_URL", "")

if not database_url:
    raise RuntimeError(
        "DATABASE_URL não configurada. "
        "Defina a variável de ambiente antes de rodar o app."
    )

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

# ─────────────────────────────────────────────
# Projetos (hardcoded após a reforma)
# ─────────────────────────────────────────────

PROJETOS_DISPONIVEIS = [
    {
        "slug": "nobel",
        "nome": "Nobel de Literatura",
        "descricao": "Ler pelo menos um livro de cada ganhador do Nobel.",
        "campo": "projeto_nobel",
    },
    {
        "slug": "mundo",
        "nome": "Lendo o Mundo",
        "descricao": "Ler um livro de autor de cada país do mundo.",
        "campo": "projeto_mundo",
    },
    {
        "slug": "postgrad",
        "nome": "PostGrad — Literatura Crítica Comparada",
        "descricao": "Livros da ementa da pós-graduação.",
        "campo": "projeto_postgrad",
    },
    {
        "slug": "tbr",
        "nome": "To-Be-Read",
        "descricao": "Livros que eu quero ler, sem projeto definido.",
        "campo": "projeto_tbr",
    },
]

PROJETOS_POR_SLUG = {p["slug"]: p for p in PROJETOS_DISPONIVEIS}

# Subprojetos de PostGrad
SUBPROJETOS_POSTGRAD = [
    {"slug": "textos_base", "nome": "Textos-Base"},
    {"slug": "literatura",  "nome": "Literatura"},
    {"slug": "eixo9",       "nome": "Eixo 9"},
]

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
# Modelo
# ─────────────────────────────────────────────

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    pais = db.Column(db.String(80), nullable=False)
    ano = db.Column(db.Integer)
    capa_url = db.Column(db.String(500), nullable=True)

    tenho = db.Column(db.Boolean, default=True, nullable=False)
    lido = db.Column(db.Boolean, default=False, nullable=False)

    cor_lombada = db.Column(db.String(20))
    estante = db.Column(db.String(20))

    projeto_nobel = db.Column(db.Boolean, default=False, nullable=False)
    projeto_mundo = db.Column(db.Boolean, default=False, nullable=False)
    projeto_postgrad = db.Column(db.Boolean, default=False, nullable=False)
    projeto_tbr = db.Column(db.Boolean, default=False, nullable=False)

    postgrad_subprojeto = db.Column(db.String(20))

    subtitulo = db.Column(db.String(200))

    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f"<Livro {self.titulo}>"

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

def chave_ordenacao_livro(livro):
    ano = livro.ano if livro.ano is not None else 0
    return (-ano, (livro.titulo or "").lower())

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

def normalizar_texto(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _extrair_campos_livro_do_form():
    """
    Extrai os campos do formulário /novo e /editar.
    Retorna um dict pronto pra criar/atualizar um Livro.
    """
    titulo = (request.form.get("titulo", "") or "").strip()
    autor = (request.form.get("autor", "") or "").strip()
    pais = (request.form.get("pais", "") or "").strip()
    capa_url = (request.form.get("capa_url", "") or "").strip()

    ano_raw = (request.form.get("ano", "") or "").strip()
    ano = None
    if ano_raw:
        try:
            ano = int(ano_raw)
        except ValueError:
            ano = None

    tenho = request.form.get("tenho", "sim") == "sim"
    lido = request.form.get("lido", "nao") == "sim"

    cor_lombada = limpar_texto(request.form.get("cor_lombada"))
    estante = limpar_texto(request.form.get("estante"))
    if not tenho:
        cor_lombada = None
        estante = None

    projeto_nobel = "projeto_nobel" in request.form
    projeto_mundo = "projeto_mundo" in request.form
    projeto_postgrad = "projeto_postgrad" in request.form
    projeto_tbr = "projeto_tbr" in request.form

    postgrad_subprojeto = None
    if projeto_postgrad:
        sub = (request.form.get("postgrad_subprojeto", "") or "").strip()
        if sub in ("textos_base", "literatura", "eixo9"):
            postgrad_subprojeto = sub

    subtitulo = limpar_texto(request.form.get("subtitulo"))

    return {
        "titulo": titulo,
        "autor": autor,
        "pais": pais,
        "ano": ano,
        "capa_url": capa_url,
        "tenho": tenho,
        "lido": lido,
        "cor_lombada": cor_lombada,
        "estante": estante.upper() if estante else None,
        "projeto_nobel": projeto_nobel,
        "projeto_mundo": projeto_mundo,
        "projeto_postgrad": projeto_postgrad,
        "projeto_tbr": projeto_tbr,
        "postgrad_subprojeto": postgrad_subprojeto,
        "subtitulo": subtitulo,
    }

def _validar_campos_livro(dados):
    """Retorna mensagem de erro, ou None se estiver tudo ok."""
    if not dados["titulo"]:
        return "Título é obrigatório."
    if not dados["autor"]:
        return "Autor é obrigatório."
    if not dados["pais"]:
        return "País é obrigatório."
    if dados["tenho"]:
        if not dados["cor_lombada"]:
            return "Lombada é obrigatória quando você tem o livro."
        if not dados["estante"]:
            return "Estante é obrigatória quando você tem o livro."
    if dados["projeto_tbr"]:
        if dados["projeto_nobel"] or dados["projeto_mundo"] or dados["projeto_postgrad"]:
            return "TBR é exclusivo: não pode ser marcado junto com outros projetos."
    return None

def _buscar_livros_duplicados(titulo, autor, ignorar_id=None):
    """
    Retorna lista de livros com mesmo título + autor (normalizados).
    Se ignorar_id for passado, pula esse livro (caso da edição).
    """
    titulo_norm = normalizar_texto(titulo)
    autor_norm = normalizar_texto(autor)

    if not titulo_norm or not autor_norm:
        return []

    query = Livro.query
    if ignorar_id is not None:
        query = query.filter(Livro.id != ignorar_id)

    candidatos = []
    for livro in query.all():
        if (normalizar_texto(livro.titulo) == titulo_norm
                and normalizar_texto(livro.autor) == autor_norm):
            candidatos.append(livro)
    return candidatos

def _serializar_duplicados(livros):
    """Transforma os livros duplicados em dicts simples pro template."""
    return [
        {
            "id": lv.id,
            "titulo": lv.titulo,
            "autor": lv.autor,
            "pais": lv.pais,
            "ano": lv.ano,
            "estante": lv.estante or "",
            "cor_lombada": lv.cor_lombada or "",
            "tenho": lv.tenho,
            "lido": lv.lido,
        }
        for lv in livros
    ]

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

def montar_dados_do_mapa():
    """
    Monta os dados do mapa do Lendo o Mundo.
    Considera APENAS livros com projeto_mundo=True e lido=True.
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

    livros = Livro.query.filter(
        Livro.projeto_mundo.is_(True),
        Livro.lido.is_(True),
    ).all()

    for lv in livros:
        codigo = codigo_pais_do_texto(lv.pais)
        if codigo:
            adicionar(codigo, PAISES_CANONICOS[codigo], lv.titulo, lv.autor, lv.capa_url)
        else:
            chave = (lv.pais or "").strip() or "(sem país)"
            nao_reconhecidos.setdefault(chave, []).append({
                "titulo": lv.titulo or "(sem título)",
                "autor": lv.autor or "",
                "origem": "projeto",
            })

    return dados, nao_reconhecidos

def resumo_do_mapa(dados_mapa):
    """Resumo do mapa. Total sempre usa a lista canônica (249)."""
    return {
        "paises_lidos": len(dados_mapa),
        "total_paises": len(PAISES_CANONICOS),
    }

def _montar_livros_lidos_do_projeto(dados_mapa):
    """Achata os livros do mapa numa lista ordenada por país/título.

    Cada item inclui tenho e lido, pra que os badges possam ser
    renderizados no template.
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
                "tenho": True,
                "lido": True,
            })
    livros.sort(key=lambda lv: (lv["pais"].lower(), lv["titulo"].lower()))
    return livros

def _conjunto_paises_lidos():
    """Códigos ISO-2 de países com pelo menos um livro do Lendo o Mundo lido."""
    codigos = set()
    livros = Livro.query.filter(
        Livro.projeto_mundo.is_(True),
        Livro.lido.is_(True),
    ).all()
    for lv in livros:
        codigo = codigo_pais_do_texto(lv.pais)
        if codigo:
            codigos.add(codigo)
    return codigos

def listar_paises_do_projeto(filtro):
    lidos = _conjunto_paises_lidos()

    livros_mundo = Livro.query.filter(
        Livro.projeto_mundo.is_(True),
        Livro.lido.is_(False),
    ).all()
    com_rec = set()
    contagem_rec = {}
    for lv in livros_mundo:
        codigo = codigo_pais_do_texto(lv.pais)
        if codigo:
            com_rec.add(codigo)
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

def listar_livros_do_pais(codigo):
    """
    Retorna (lidos, nao_lidos) de um país no Lendo o Mundo.
    """
    livros = Livro.query.filter(Livro.projeto_mundo.is_(True)).all()
    do_pais = [
        lv for lv in livros
        if codigo_pais_do_texto(lv.pais) == codigo
    ]
    do_pais.sort(key=chave_ordenacao_livro)
    lidos = [lv for lv in do_pais if lv.lido]
    nao_lidos = [lv for lv in do_pais if not lv.lido]
    return lidos, nao_lidos

def _query_do_projeto(campo):
    """Retorna a query base de todos os livros daquele projeto."""
    return Livro.query.filter(getattr(Livro, campo).is_(True))

def _contar_por_status(livros):
    """Dado uma lista de livros, retorna dict com as 5 contagens.

    Obs.: posse e leitura são dimensões diferentes; os números
    NÃO são mutuamente exclusivos.
    """
    return {
        "total": len(livros),
        "tenho": sum(1 for lv in livros if lv.tenho),
        "nao_tenho": sum(1 for lv in livros if not lv.tenho),
        "lidos": sum(1 for lv in livros if lv.lido),
        "nao_lidos": sum(1 for lv in livros if not lv.lido),
    }

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

    # Se NÃO tem busca ativa, mostra só os que tenho
    if not busca:
        query = query.filter(Livro.tenho.is_(True))

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
        livro.capa_final = livro.capa_url or None

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
        [e for (e,) in db.session.query(Livro.estante).filter(
            Livro.tenho.is_(True)
        ).distinct().all() if e],
        key=chave_ordenacao_estante_simples,
    )

    paises_disponiveis = sorted(
        [p for (p,) in db.session.query(Livro.pais).filter(
            Livro.tenho.is_(True)
        ).distinct().all() if p],
        key=lambda s: normalizar_texto(s),
    )

    args_atuais = request.args.to_dict(flat=True)
    next_url = request.path
    if args_atuais:
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
    next_url = url_next_valida(request.args.get("next") or request.form.get("next"))
    projeto_pre = request.args.get("projeto", "").strip().lower()
    pais_pre = request.args.get("pais", "").strip()

    if request.method == "POST":
        dados = _extrair_campos_livro_do_form()
        erro = _validar_campos_livro(dados)
        if erro:
            return render_template(
                "novo.html",
                cores=CORES_ORDEM,
                valores=dados,
                erro=erro,
                next_url=next_url,
                projetos=PROJETOS_DISPONIVEIS,
                subprojetos=SUBPROJETOS_POSTGRAD,
                duplicados=None,
                modo_duplicado=False,
            ), 400

        forcar = request.form.get("forcar_salvar") == "1"
        duplicados = []
        if not forcar:
            duplicados = _buscar_livros_duplicados(dados["titulo"], dados["autor"])

        if duplicados and not forcar:
            return render_template(
                "novo.html",
                cores=CORES_ORDEM,
                valores=dados,
                erro=None,
                next_url=next_url,
                projetos=PROJETOS_DISPONIVEIS,
                subprojetos=SUBPROJETOS_POSTGRAD,
                duplicados=_serializar_duplicados(duplicados),
                modo_duplicado=True,
            ), 200

        livro = Livro(**dados)
        db.session.add(livro)
        db.session.commit()

        if next_url:
            return redirect(next_url)
        return redirect(url_for("home"))

    # GET
    valores = {}
    if pais_pre:
        valores["pais"] = pais_pre
    if projeto_pre and projeto_pre in PROJETOS_POR_SLUG:
        campo = PROJETOS_POR_SLUG[projeto_pre]["campo"]
        valores[campo] = True

    return render_template(
        "novo.html",
        cores=CORES_ORDEM,
        valores=valores,
        erro=None,
        next_url=next_url,
        projetos=PROJETOS_DISPONIVEIS,
        subprojetos=SUBPROJETOS_POSTGRAD,
        duplicados=None,
        modo_duplicado=False,
    )

@app.route("/editar/<int:livro_id>", methods=["GET", "POST"])
def editar(livro_id):
    livro = db.get_or_404(Livro, livro_id)
    next_url = url_next_valida(request.args.get("next") or request.form.get("next"))

    if request.method == "POST":
        dados = _extrair_campos_livro_do_form()
        erro = _validar_campos_livro(dados)
        if erro:
            return render_template(
                "editar.html",
                livro=livro,
                valores=dados,
                cores=CORES_ORDEM,
                erro=erro,
                next_url=next_url,
                projetos=PROJETOS_DISPONIVEIS,
                subprojetos=SUBPROJETOS_POSTGRAD,
                duplicados=None,
                modo_duplicado=False,
            ), 400

        forcar = request.form.get("forcar_salvar") == "1"
        duplicados = []
        if not forcar:
            duplicados = _buscar_livros_duplicados(
                dados["titulo"], dados["autor"], ignorar_id=livro.id
            )

        if duplicados and not forcar:
            return render_template(
                "editar.html",
                livro=livro,
                valores=dados,
                cores=CORES_ORDEM,
                erro=None,
                next_url=next_url,
                projetos=PROJETOS_DISPONIVEIS,
                subprojetos=SUBPROJETOS_POSTGRAD,
                duplicados=_serializar_duplicados(duplicados),
                modo_duplicado=True,
            ), 200

        for campo, valor in dados.items():
            setattr(livro, campo, valor)
        db.session.commit()

        if next_url:
            return redirect(next_url)
        return redirect(url_for("home"))

    valores = {
        "titulo": livro.titulo,
        "autor": livro.autor,
        "pais": livro.pais,
        "ano": livro.ano,
        "capa_url": livro.capa_url,
        "tenho": livro.tenho,
        "lido": livro.lido,
        "cor_lombada": livro.cor_lombada,
        "estante": livro.estante,
        "projeto_nobel": livro.projeto_nobel,
        "projeto_mundo": livro.projeto_mundo,
        "projeto_postgrad": livro.projeto_postgrad,
        "projeto_tbr": livro.projeto_tbr,
        "postgrad_subprojeto": livro.postgrad_subprojeto,
        "subtitulo": livro.subtitulo,
    }

    return render_template(
        "editar.html",
        livro=livro,
        valores=valores,
        cores=CORES_ORDEM,
        erro=None,
        next_url=next_url,
        projetos=PROJETOS_DISPONIVEIS,
        subprojetos=SUBPROJETOS_POSTGRAD,
        duplicados=None,
        modo_duplicado=False,
    )

@app.route("/excluir/<int:livro_id>", methods=["GET", "POST"])
def excluir(livro_id):
    livro = db.get_or_404(Livro, livro_id)
    next_url = url_next_valida(request.args.get("next") or request.form.get("next"))

    if request.method == "POST":
        db.session.delete(livro)
        db.session.commit()
        if next_url:
            return redirect(next_url)
        return redirect(url_for("home"))

    return render_template("excluir.html", livro=livro, next_url=next_url)

@app.route("/estatisticas")
def estatisticas():
    # Topo: TODOS os livros do sistema (físicos + não físicos)
    total = Livro.query.count()
    tenho = Livro.query.filter(Livro.tenho.is_(True)).count()
    nao_tenho = Livro.query.filter(Livro.tenho.is_(False)).count()
    total_lidos = Livro.query.filter(Livro.lido.is_(True)).count()
    total_nao_lidos = Livro.query.filter(Livro.lido.is_(False)).count()

    pct_lidos = round(total_lidos / total * 100) if total > 0 else 0

    # Blocos internos: só biblioteca física (tenho=True)
    total_com_projeto = Livro.query.filter(
        Livro.tenho.is_(True),
        db.or_(
            Livro.projeto_nobel.is_(True),
            Livro.projeto_mundo.is_(True),
            Livro.projeto_postgrad.is_(True),
            Livro.projeto_tbr.is_(True),
        )
    ).count()
    total_sem_projeto = tenho - total_com_projeto

    total_autores_distintos = (
        db.session.query(db.func.count(db.func.distinct(Livro.autor)))
        .filter(Livro.tenho.is_(True))
        .scalar() or 0
    )
    total_paises_distintos = (
        db.session.query(db.func.count(db.func.distinct(Livro.pais)))
        .filter(Livro.tenho.is_(True))
        .scalar() or 0
    )

    por_estante_raw = (
        db.session.query(Livro.estante, db.func.count(Livro.id))
        .filter(Livro.tenho.is_(True))
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
        .filter(Livro.tenho.is_(True))
        .group_by(Livro.autor)
        .order_by(db.func.count(Livro.id).desc(), Livro.autor.asc())
        .all()
    )

    por_pais = (
        db.session.query(Livro.pais, db.func.count(Livro.id))
        .filter(Livro.tenho.is_(True))
        .group_by(Livro.pais)
        .order_by(db.func.count(Livro.id).desc())
        .all()
    )

    por_cor_raw = dict(
        db.session.query(Livro.cor_lombada, db.func.count(Livro.id))
        .filter(Livro.tenho.is_(True))
        .group_by(Livro.cor_lombada)
        .all()
    )
    por_cor = [(cor, por_cor_raw.get(cor, 0)) for cor in CORES_ORDEM]
    sem_cor = por_cor_raw.get(None, 0)

    return render_template(
        "estatisticas.html",
        total=total,
        tenho=tenho,
        nao_tenho=nao_tenho,
        total_lidos=total_lidos,
        total_nao_lidos=total_nao_lidos,
        pct_lidos=pct_lidos,
        total_literarios=total_com_projeto,
        total_nao_literarios=total_sem_projeto,
        total_autores_distintos=total_autores_distintos,
        total_paises_distintos=total_paises_distintos,
        por_estante=por_estante,
        top_autores=top_autores,
        por_pais=por_pais,
        por_cor=por_cor,
        sem_cor=sem_cor,
        cores_hex=CORES_HEX,
    )

@app.route("/lidos")
def lidos():
    filtro = request.args.get("filtro", "todos").strip()
    if filtro not in ("todos", "tenho", "nao_tenho"):
        filtro = "todos"

    # Base: todos os livros lidos
    query = Livro.query.filter(Livro.lido.is_(True))

    if filtro == "tenho":
        query = query.filter(Livro.tenho.is_(True))
    elif filtro == "nao_tenho":
        query = query.filter(Livro.tenho.is_(False))

    livros = query.all()
    livros.sort(key=chave_ordenacao_livro)

    # Contagens (sempre sobre lidos)
    total_lidos = Livro.query.filter(Livro.lido.is_(True)).count()
    total_lidos_tenho = Livro.query.filter(
        Livro.lido.is_(True), Livro.tenho.is_(True)
    ).count()
    total_lidos_nao_tenho = Livro.query.filter(
        Livro.lido.is_(True), Livro.tenho.is_(False)
    ).count()

    return render_template(
        "lidos.html",
        livros=livros,
        filtro=filtro,
        total_lidos=total_lidos,
        total_lidos_tenho=total_lidos_tenho,
        total_lidos_nao_tenho=total_lidos_nao_tenho,
    )

@app.route("/backup")
def backup():
    livros = Livro.query.order_by(Livro.id).all()

    agora = datetime.now()
    data_iso = agora.strftime("%Y-%m-%d %H:%M:%S")
    data_arquivo = agora.strftime("%Y%m%d-%H%M")

    linhas = []
    linhas.append("-- Dark Library — Backup")
    linhas.append(f"-- Gerado em: {data_iso}")
    linhas.append(f"-- Livros: {len(livros)}")
    linhas.append("")
    linhas.append("-- Restauração:")
    linhas.append("-- 1. Abra o SQL Editor do Neon.")
    linhas.append("-- 2. Cole este arquivo inteiro e execute de uma vez.")
    linhas.append("-- 3. ATENÇÃO: o DELETE abaixo APAGA os dados atuais.")
    linhas.append("")
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
                sql_escape(livro.ano),
                sql_escape(livro.capa_url),
                sql_escape(livro.tenho),
                sql_escape(livro.lido),
                sql_escape(livro.cor_lombada),
                sql_escape(livro.estante),
                sql_escape(livro.projeto_nobel),
                sql_escape(livro.projeto_mundo),
                sql_escape(livro.projeto_postgrad),
                sql_escape(livro.projeto_tbr),
                sql_escape(livro.postgrad_subprojeto),
                sql_escape(livro.subtitulo),
                sql_escape(livro.criado_em),
            ])
            linhas.append(
                "INSERT INTO livro "
                "(id, titulo, autor, pais, ano, capa_url, tenho, lido, cor_lombada, estante, "
                "projeto_nobel, projeto_mundo, projeto_postgrad, projeto_tbr, "
                "postgrad_subprojeto, subtitulo, criado_em) "
                f"VALUES ({valores});"
            )
    linhas.append("")

    linhas.append("-- Ajuste da sequence")
    linhas.append(
        "SELECT setval(pg_get_serial_sequence('livro', 'id'), "
        "COALESCE((SELECT MAX(id) FROM livro), 0) + 1, false);"
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

# ─────────────────────────────────────────────
# Rotas — projetos
# ─────────────────────────────────────────────

@app.route("/projetos")
def projetos():
    projetos_com_contagem = []
    for p in PROJETOS_DISPONIVEIS:
        campo = p["campo"]

        if p["slug"] == "mundo":
            dados_mapa, _ = montar_dados_do_mapa()
            resumo = resumo_do_mapa(dados_mapa)
            total = resumo["total_paises"]
            lidos = resumo["paises_lidos"]
            tipo_mundo = True
            tipo_tbr = False
            pct = round(lidos / total * 100) if total > 0 else 0
        elif p["slug"] == "tbr":
            livros = _query_do_projeto(campo).all()
            total = len(livros)
            lidos = 0
            tipo_mundo = False
            tipo_tbr = True
            pct = 0
        else:
            livros = _query_do_projeto(campo).all()
            contagens = _contar_por_status(livros)
            total = contagens["total"]
            lidos = contagens["lidos"]
            tipo_mundo = False
            tipo_tbr = False
            pct = round(lidos / total * 100) if total > 0 else 0

        projetos_com_contagem.append({
            "slug": p["slug"],
            "nome": p["nome"],
            "descricao": p["descricao"],
            "total": total,
            "lidos": lidos,
            "pct": pct,
            "tipo_mundo": tipo_mundo,
            "tipo_tbr": tipo_tbr,
        })

    return render_template("projetos.html", projetos=projetos_com_contagem)

@app.route("/projetos/<slug>")
def projeto_detalhe(slug):
    if slug not in PROJETOS_POR_SLUG:
        return f"Projeto '{slug}' não encontrado.", 404

    projeto = PROJETOS_POR_SLUG[slug]
    campo = projeto["campo"]

    livros = _query_do_projeto(campo).all()
    livros.sort(key=chave_ordenacao_livro)

    # Contagens do resumo (5 caixinhas)
    # Obs.: posse e leitura são dimensões diferentes; os números
    # NÃO são mutuamente exclusivos (um livro "tenho+lido" entra em
    # "tenho" e em "lidos"). Isso é intencional.
    contagens = _contar_por_status(livros)
    total = contagens["total"]
    tenho = contagens["tenho"]
    nao_tenho = contagens["nao_tenho"]
    lidos = contagens["lidos"]
    nao_lidos = contagens["nao_lidos"]
    pct = round(lidos / total * 100) if total > 0 else 0

    # Filtros em cápsula
    filtro = request.args.get("filtro", "lido").strip()
    if slug == "tbr":
        # TBR: filtros são Todos / Tenho / Não Tenho
        if filtro not in ("todos", "tenho", "nao_tenho"):
            filtro = "todos"
    elif slug == "mundo":
        # Mundo: filtros são Todos / Lido / Não Lido / Tenho / Não Tenho / Recomendações
        if filtro not in ("todos", "lido", "nao_lido", "tenho", "nao_tenho", "recomendacoes"):
            filtro = "todos"
    else:
        if filtro not in ("lido", "nao_lido", "tenho", "recomendacoes", "todos"):
            filtro = "lido"

    livros_filtrados = livros
    if slug == "tbr":
        if filtro == "tenho":
            livros_filtrados = [lv for lv in livros if lv.tenho]
        elif filtro == "nao_tenho":
            livros_filtrados = [lv for lv in livros if not lv.tenho]
        # "todos" = sem filtro adicional
    elif slug == "mundo":
        if filtro == "lido":
            livros_filtrados = [lv for lv in livros if lv.lido]
        elif filtro == "nao_lido":
            livros_filtrados = [lv for lv in livros if not lv.lido]
        elif filtro == "tenho":
            livros_filtrados = [lv for lv in livros if lv.tenho]
        elif filtro == "nao_tenho":
            livros_filtrados = [lv for lv in livros if not lv.tenho]
        elif filtro == "recomendacoes":
            livros_filtrados = [lv for lv in livros if not lv.tenho and not lv.lido]
        # "todos" = sem filtro adicional
    else:
        if filtro == "lido":
            livros_filtrados = [lv for lv in livros if lv.lido]
        elif filtro == "nao_lido":
            livros_filtrados = [lv for lv in livros if not lv.lido]
        elif filtro == "tenho":
            livros_filtrados = [lv for lv in livros if lv.tenho and not lv.lido]
        elif filtro == "recomendacoes":
            livros_filtrados = [lv for lv in livros if not lv.tenho and not lv.lido]
        # "todos" = sem filtro adicional

    # Dados do mapa (só pra mundo)
    dados_mapa = None
    paises_nao_reconhecidos = None
    resumo_mapa = None
    livros_lidos_projeto = None

    if slug == "mundo":
        dados_mapa, paises_nao_reconhecidos = montar_dados_do_mapa()
        resumo_mapa = resumo_do_mapa(dados_mapa)
        livros_lidos_projeto = _montar_livros_lidos_do_projeto(dados_mapa)

    template_map = {
        "nobel": "projeto_nobel.html",
        "mundo": "projeto_mundo.html",
        "postgrad": "projeto_postgrad.html",
        "tbr": "projeto_tbr.html",
    }
    template = template_map[slug]

    return render_template(
        template,
        projeto=projeto,
        slug=slug,
        livros=livros,
        livros_filtrados=livros_filtrados,
        total=total,
        tenho=tenho,
        nao_tenho=nao_tenho,
        lidos=lidos,
        nao_lidos=nao_lidos,
        pct=pct,
        filtro=filtro,
        subprojetos=SUBPROJETOS_POSTGRAD,
        dados_mapa=dados_mapa,
        paises_nao_reconhecidos=paises_nao_reconhecidos,
        resumo_mapa=resumo_mapa,
        livros_lidos_projeto=livros_lidos_projeto,
    )

@app.route("/projetos/<slug>/paises")
def projeto_paises(slug):
    if slug != "mundo":
        return "Só o projeto Lendo o Mundo tem lista de países.", 404

    projeto = PROJETOS_POR_SLUG[slug]

    filtro = request.args.get("filtro", "lidos").strip()
    if filtro not in ("lidos", "nao_lidos", "com_recomendacoes", "todos"):
        filtro = "lidos"

    paises = listar_paises_do_projeto(filtro)

    total_paises_lidos = sum(1 for p in paises if p["lido"]) if filtro == "todos" else len(_conjunto_paises_lidos())
    total_paises_canonicos = len(PAISES_CANONICOS)

    return render_template(
        "paises.html",
        projeto=projeto,
        slug=slug,
        paises=paises,
        filtro=filtro,
        total_paises_lidos=total_paises_lidos,
        total_paises_canonicos=total_paises_canonicos,
    )

@app.route("/projetos/<slug>/paises/<codigo>")
def projeto_pais_detalhe(slug, codigo):
    if slug != "mundo":
        return "Só o projeto Lendo o Mundo tem página de país.", 404

    codigo = (codigo or "").strip().upper()
    if codigo not in PAISES_CANONICOS:
        return f"País '{codigo}' não reconhecido.", 404

    projeto = PROJETOS_POR_SLUG[slug]
    nome = PAISES_CANONICOS[codigo]

    lidos, nao_lidos = listar_livros_do_pais(codigo)

    return render_template(
        "pais.html",
        projeto=projeto,
        slug=slug,
        codigo=codigo,
        nome=nome,
        lidos=lidos,
        nao_lidos=nao_lidos,
    )

# ─────────────────────────────────────────────
# Criação automática das tabelas
# ─────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")