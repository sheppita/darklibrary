"""
Script de migração — preenche pais_codigo nos item_projeto existentes.
Roda UMA VEZ. Depois pode apagar o arquivo.

Como rodar (no terminal, com o venv ativado):
    set "DATABASE_URL=postgresql://..."
    python migrar_pais_codigo.py
"""
import app as app_module

# O app.py tem `if __name__ == "__main__": app.run(...)` no final.
# Quando importado (não como __main__), o app.run NÃO roda. Só as
# definições e o db.create_all() são executados. É o comportamento
# que queremos.

app = app_module.app
db = app_module.db

with app.app_context():
    ItemProjeto = app_module.ItemProjeto

    itens = ItemProjeto.query.filter(ItemProjeto.pais_codigo.is_(None)).all()
    total = len(itens)
    atualizados = 0
    ignorados = 0

    print(f"Itens sem pais_codigo: {total}")

    for it in itens:
        codigo = app_module.codigo_pais_do_texto(it.pais)
        if codigo:
            it.pais_codigo = codigo
            atualizados += 1
        else:
            ignorados += 1
            print(f"  Ignorado: id={it.id}, pais='{it.pais}'")

    db.session.commit()

    print(f"\nAtualizados: {atualizados}")
    print(f"Ignorados (sem país ou país não reconhecido): {ignorados}")
    print("Migração concluída.")
    