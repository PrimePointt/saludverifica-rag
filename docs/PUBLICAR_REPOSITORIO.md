# Publicar el repositorio

Nombre recomendado: **sistema-verificacion-salud-rag**. Visibilidad: **público**.

Repositorio Git local ya inicializado. GitHub remoto no creado desde este entorno: herramienta `gh` no está disponible. No hay commits ni archivos subidos automáticamente.

## GitHub web + Git

1. En GitHub, crea repositorio público con nombre anterior.
2. No añadas README, licencia ni `.gitignore` desde GitHub: proyecto ya contiene README y exclusiones.
3. Desde esta carpeta, revisa archivos antes de publicar:

```bash
git status
git diff
```

4. Revisa que `.env`, `storage/` y claves no aparezcan. Después, cuando decidas publicar:

```bash
git add .dockerignore .env.example .gitignore .streamlit Dockerfile README.md app compose.yaml data docs requirements.txt streamlit_app.py tests
git commit -m "feat: add containerized health evidence demo"
git remote add origin https://github.com/TU_USUARIO/sistema-verificacion-salud-rag.git
git push -u origin main
```

Sustituye `TU_USUARIO` por usuario real. Git puede pedir autenticación de GitHub.

5. En equipo destino, clona URL real y sigue README. Construye y prueba hoy; no esperes al momento de exposición.

Extractos oficiales incluidos tienen atribución y fines académicos. Antes de comercializar distribución de contenidos, revisar condiciones de fuentes y elegir licencia para código del equipo.
