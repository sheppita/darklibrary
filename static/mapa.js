// ─────────────────────────────────────────────
// mapa.js — carrega o SVG do mundo e pinta os países
// ─────────────────────────────────────────────

(function () {
    "use strict";

        const COR_NAO_LIDA = "#e5e1d8";    // bege claro (mesmo tom das bordas)

    // Paleta curada: cores vivas, mas não neon, com boa harmonia entre si.
    // 24 tons, distribuídos em torno do círculo cromático.
    const PALETA = [
        "#c0392b", // vermelho
        "#d35400", // laranja
        "#d68910", // âmbar
        "#b7950b", // mostarda
        "#7d8c1f", // oliva
        "#4a7c59", // verde-musgo
        "#229954", // verde
        "#148f77", // verde-água
        "#1a7a82", // ciano escuro
        "#2e86c1", // azul
        "#2c5aa0", // azul profundo
        "#4a4a9c", // índigo
        "#6c3d8c", // roxo
        "#8e44ad", // púrpura
        "#a3327c", // magenta escuro
        "#c2185b", // rosa-escuro
        "#b9770e", // terra
        "#7e5109", // marrom claro
        "#5d4037", // marrom
        "#4e342e", // café
        "#2c3e50", // ardósia
        "#455a64", // cinza-azulado
        "#566573", // cinza quente
        "#935116", // cobre
    ];

    // Hash simples (djb2) para transformar uma string num inteiro.
    // Usado para escolher a cor da paleta de forma determinística.
    function hashString(s) {
        let h = 5381;
        for (let i = 0; i < s.length; i++) {
            h = ((h << 5) + h) + s.charCodeAt(i);
            h = h & 0xffffffff; // mantém em 32 bits
        }
        return Math.abs(h);
    }

    function corDoPais(codigoIso) {
        const idx = hashString(codigoIso.toLowerCase()) % PALETA.length;
        return PALETA[idx];
    }

    const elMapa = document.getElementById("mapa-svg");
    if (!elMapa) {
        return; // Não estamos numa página com mapa.
    }

    const elPopup = document.getElementById("mapa-popup");
    const elPopupTitulo = document.getElementById("mapa-popup-titulo");
    const elPopupLista = document.getElementById("mapa-popup-lista");
    const elPopupFechar = document.getElementById("mapa-popup-fechar");

    // Lê os dados que o Flask injetou no atributo data-dados.
    let dados = {};
    try {
        const bruto = elMapa.getAttribute("data-dados") || "{}";
        dados = JSON.parse(bruto);
    } catch (e) {
        console.error("Erro ao ler dados do mapa:", e);
        dados = {};
    }

    // Normaliza as chaves de dados para minúsculas, porque o SVG
    // que baixamos usa ids em minúsculo (br, us, gb).
    const dadosMinusculos = {};
    Object.keys(dados).forEach(function (chave) {
        dadosMinusculos[chave.toLowerCase()] = dados[chave];
    });

    function fecharPopup() {
        elPopup.hidden = true;
        const elLink = document.getElementById("mapa-popup-link-pais");
        if (elLink) {
            elLink.hidden = true;
        }
    }

    function abrirPopup(codigo, info) {
        elPopupTitulo.textContent = info.nome + " (" + info.total + ")";

        elPopupLista.innerHTML = "";
        info.livros.forEach(function (livro) {
            const li = document.createElement("li");
            li.className = "mapa-popup-item";

            const titulo = document.createElement("span");
            titulo.className = "mapa-popup-livro-titulo";
            titulo.textContent = livro.titulo;
            li.appendChild(titulo);

            if (livro.autor) {
                const autor = document.createElement("span");
                autor.className = "mapa-popup-livro-autor";
                autor.textContent = livro.autor;
                li.appendChild(autor);
            }

            const origem = document.createElement("span");
            origem.className = "mapa-popup-livro-origem";
            origem.textContent = livro.origem === "projeto" ? "projeto" : "estante";
            li.appendChild(origem);

            elPopupLista.appendChild(li);
        });

        // Link "Ver detalhes do país →", se a página tiver o dado do projeto
        const elLink = document.getElementById("mapa-popup-link-pais");
        if (elLink) {
            // Monta a URL a partir de um "template" no HTML.
            // O HTML já tem a URL base sem o código no final.
            const base = elLink.getAttribute("data-url-base");
            if (base) {
                elLink.href = base + codigo;
                elLink.hidden = false;
            }
        }

        elPopup.hidden = false;
    }

    // Carrega o SVG e injeta no DOM.
    fetch("/static/mundo.svg")
        .then(function (resp) {
            if (!resp.ok) {
                throw new Error("HTTP " + resp.status);
            }
            return resp.text();
        })
        .then(function (svgTexto) {
            elMapa.innerHTML = svgTexto;

            const svg = elMapa.querySelector("svg");
            if (!svg) {
                console.error("SVG não encontrado após injeção.");
                return;
            }

            // Ajusta o SVG para ocupar o container.
            svg.removeAttribute("width");
            svg.removeAttribute("height");
            svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
            svg.style.width = "100%";
            svg.style.height = "auto";
            svg.style.display = "block";

            // Pinta os países que têm dados.
            Object.keys(dadosMinusculos).forEach(function (codigoMin) {
                const info = dadosMinusculos[codigoMin];

                // O SVG usa ids em minúsculo. Algumas variantes usam
                // seletores por id, outras por classe .country.
                let path = svg.querySelector("#" + codigoMin);
                if (!path) {
                    // Tenta caixa alta, por segurança.
                    path = svg.querySelector("#" + codigoMin.toUpperCase());
                }
                if (!path) {
                    return;
                }

                path.style.fill = corDoPais(codigoMin);
                path.style.cursor = "pointer";
                path.classList.add("pais-lido");

                path.addEventListener("click", function (ev) {
                    ev.stopPropagation();
                    abrirPopup(codigoMin, info);
                });

                path.addEventListener("mouseenter", function () {
                    path.style.filter = "brightness(0.92)";
                });
                path.addEventListener("mouseleave", function () {
                    path.style.filter = "";
                });
            });

            // Cor de fundo para todos os países (não lidos).
            svg.querySelectorAll("path").forEach(function (p) {
                if (!p.style.fill) {
                    p.style.fill = COR_NAO_LIDA;
                    p.style.stroke = "#f7f5f0";
                    p.style.strokeWidth = "0.5";
                }
            });

            // Clique no mapa (fora de país) fecha o popup.
            svg.addEventListener("click", function () {
                fecharPopup();
            });
        })
        .catch(function (erro) {
            console.error("Erro ao carregar o SVG do mapa:", erro);
            elMapa.innerHTML = '<p class="mapa-erro">Não foi possível carregar o mapa.</p>';
        });

    if (elPopupFechar) {
        elPopupFechar.addEventListener("click", fecharPopup);
    }

    document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") {
            fecharPopup();
        }
    });

})();