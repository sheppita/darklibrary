"""
Script de migração — Etapa 20 (Reforma dos Projetos)

Converte os registros de `item_projeto` em registros de `livro`
com os novos campos booleanos de projeto.

Roda UMA VEZ. Depois pode apagar o arquivo.

Como rodar (no terminal, com o venv ativado):
    set "DATABASE_URL=postgresql://..."
    python migrar_reforma.py

O que faz:
    1. Para cada ItemProjeto:
       - Se tem livro_id vinculado → marca projeto_* no livro existente
       - Se não tem → cria Livro novo com os dados do item
    2. Apaga todos os registros de item_projeto
    3. Apaga a tabela item_projeto
    4. Apaga todos os registros de projeto
    5. Apaga a tabela projeto
    6. Reporta o que foi feito

O site NÃO quebra durante a migração — o app.py antigo não conhece
as colunas novas e continua funcionando com o modelo antigo.
"""
import app as app_module
from datetime import datetime

app = app_module.app
db = app_module.db
Livro = app_module.Livro
Projeto = app_module.Projeto
ItemProjeto = app_module.ItemProjeto


# ═══════════════════════════════════════════════════════════
# Mapeamentos
# ═══════════════════════════════════════════════════════════

# projeto.tipo → nome do campo booleano no Livro
MAPA_TIPO_PROJETO = {
    "nobel":     "projeto_nobel",
    "mundo":     "projeto_mundo",
    "postgrad":  "projeto_postgrad",
    "tbr":       "projeto_tbr",
}


def derivar_status(status_item):
    """Deriva (tenho, lido) a partir do status antigo."""
    if status_item == "li":
        return True, True
    elif status_item == "tenho_nao_li":
        return True, False
    else:  # nao_tenho
        return False, False


def projeto_do_item(item):
    """Retorna o campo booleano correspondente ao tipo do projeto."""
    tipo = (item.projeto.tipo or "").strip().lower()
    return MAPA_TIPO_PROJETO.get(tipo)


def migrar():
    with app.app_context():
        print("═" * 60)
        print("Migração Etapa 20 — Reforma dos Projetos")
        print("═" * 60)
        print()

        itens = ItemProjeto.query.all()
        total_itens = len(itens)
        print(f"Itens de projeto encontrados: {total_itens}")
        print()

        livros_criados = 0
        livros_marcados = 0
        itens_sem_tipo_conhecido = []

        for i, item in enumerate(itens, start=1):
            campo_projeto = projeto_do_item(item)

            if campo_projeto is None:
                itens_sem_tipo_conhecido.append(item)
                print(f"  [{i}/{total_itens}] ⚠️  Item {item.id} "
                      f"(projeto '{item.projeto.nome}', tipo "
                      f"'{item.projeto.tipo}') — tipo desconhecido, ignorado")
                continue

            if item.livro_id is not None:
                # Já tem livro vinculado → só marca o projeto
                livro = item.livro
                if livro is None:
                    print(f"  [{i}/{total_itens}] ⚠️  Item {item.id} tem "
                          f"livro_id={item.livro_id} mas o livro não existe. Ignorado.")
                    continue
                setattr(livro, campo_projeto, True)
                livros_marcados += 1
                print(f"  [{i}/{total_itens}] ✓ Livro {livro.id} "
                      f"marcado como {campo_projeto}")
            else:
                # Cria livro novo
                tenho, lido = derivar_status(item.status)
                pais = item.pais if item.pais else "(A Definir)"
                capa_url = item.capa_url if item.capa_url else ""

                livro = Livro(
                    titulo=item.titulo,
                    autor=item.autor,
                    pais=pais,
                    ano=item.ano,
                    capa_url=capa_url,
                    tenho=tenho,
                    lido=lido,
                    cor_lombada=None,
                    estante=None,
                    subtitulo=item.subtitulo,
                    criado_em=item.criado_em or datetime.utcnow(),
                )
                setattr(livro, campo_projeto, True)
                db.session.add(livro)
                livros_criados += 1

                if i % 20 == 0 or i == total_itens:
                    print(f"  [{i}/{total_itens}] ✓ Criando livros... "
                          f"({livros_criados} até agora)")

        db.session.commit()
        print()
        print(f"✓ {livros_criados} livros criados")
        print(f"✓ {livros_marcados} livros existentes marcados")
        if itens_sem_tipo_conhecido:
            print(f"⚠️  {len(itens_sem_tipo_conhecido)} itens ignorados "
                  f"(tipo de projeto desconhecido)")
        print()

        # ─────────────────────────────────────────────
        # Apagar tabelas antigas
        # ─────────────────────────────────────────────

        print("Apagando tabelas antigas...")

        db.session.execute(db.text("DELETE FROM item_projeto"))
        db.session.commit()
        print("✓ DELETE FROM item_projeto")

        db.session.execute(db.text("DROP TABLE item_projeto"))
        db.session.commit()
        print("✓ DROP TABLE item_projeto")

        db.session.execute(db.text("DELETE FROM projeto"))
        db.session.commit()
        print("✓ DELETE FROM projeto")

        db.session.execute(db.text("DROP TABLE projeto"))
        db.session.commit()
        print("✓ DROP TABLE projeto")

        print()
        print("═" * 60)
        print("Migração concluída com sucesso.")
        print("═" * 60)


if __name__ == "__main__":
    migrar()