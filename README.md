# alphaisolation.be

Site vitrine d'Alpha Isolation (ALGO FAÇADE SRL, Courcelles) : HTML et CSS statiques, avec un CMS (Decap CMS) pour les
**réalisations** et les **conseils** (le blog).

## Arborescence
- `*.html` : pages du site (accueil, 3 services, 6 pages villes, contact, À propos, pages légales, `merci.html`, `404.html`)
- `realisations.html`, `realisation-*.html`, `conseils.html`, `conseils-*.html` : **générées** à partir de `contenu/`.
  Ne pas modifier à la main les fiches et les articles, ni les zones `<!-- REALISATIONS -->` et `<!-- CONSEILS -->`.
- `contenu/realisations/*.json` : un fichier par chantier · `contenu/conseils/*.json` : un fichier par article
- `outils/build.py` : générateur (fiches, articles, images redimensionnées, sitemap)
- `admin/` : interface d'administration Decap CMS (`/admin/`)
- `css/` · `fonts/` · `js/lightbox.js` (visionneuse photo et vidéo) · `img/photos/` (photos d'origine, WebP)
- `img/uploads/` : fichiers envoyés via le CMS · `img/gen/` : versions optimisées créées au build (non versionnées)
- `_modeles/og-image.html` : source de l'image de partage `img/og-alpha-isolation.jpg`
- `netlify.toml` : build, redirections des anciennes URLs WordPress, en-têtes HTTP
- `A-COMPLETER.md` : contenus en attente du client (notes internes, gardées en local et exclues du dépôt)

## Utiliser le CMS
Aller sur **https://www.alphaisolation.be/admin/** et se connecter avec GitHub.
- **Réalisations** : titre, catégorie, travaux, résumé, description, commune, année, surface, durée, photos (la
  première sert de couverture), vidéos MP4 courtes ou liens YouTube. Décocher « Publié » masque le chantier.
- **Conseils (blog)** : titre, statut (*Publié* / *À venir* : annoncé sans lien / *Brouillon* : invisible), date,
  catégorie, résumé, image, texte de l'article. Dans le texte, une citation s'affiche comme un encadré vert.
- Les photos peuvent être envoyées telles quelles depuis un téléphone (JPG) : le build crée les versions WebP 700 et 1400 px.
- Après chaque enregistrement, Netlify reconstruit le site, ce qui prend 1 à 2 minutes.

## Mise en ligne (GitHub + Netlify)
1. Dépôt GitHub : `alpha-isolation/alpha-isolation` (organisation dédiée au client). Si le dépôt change de nom, mettre à jour
   `repo:` dans `admin/config.yml`.
2. Netlify : *Add new site → Import from Git*. Le build (`python outils/build.py`) et le dossier publié (`.`) sont déjà
   dans `netlify.toml`, et Netlify installe `requirements.txt` tout seul.
3. **Connexion au CMS** (une seule fois) :
   - sur GitHub : *Settings → Developer settings → OAuth Apps → New OAuth App*, avec comme
     *Authorization callback URL* : `https://api.netlify.com/auth/done` ;
   - sur Netlify : *Site configuration → Access & security → OAuth → Install provider → GitHub*, puis coller le
     Client ID et le Client secret ;
   - toute personne qui doit modifier le site a besoin d'un accès en écriture au dépôt GitHub.
4. **Formulaires** : *Forms → Enable form detection*, puis une notification e-mail vers info@alphaisolation.be.
   Le formulaire s'appelle `devis`, et le champ caché `page` indique la page d'origine de la demande.
5. **Domaine** : `www.alphaisolation.be` comme domaine principal, puis le DNS (aujourd'hui chez OVH, via Cloudflare).

## Travailler en local
```bash
pip install -r requirements.txt
```
```bash
python outils/build.py
```
```bash
python -m http.server 8765
```
Puis ouvrir http://localhost:8765. Pour utiliser l'admin en local sans GitHub, lancer aussi `npx decap-server` à la
racine du projet et ouvrir http://localhost:8765/admin/. Après avoir modifié du contenu, relancer `python outils/build.py`.
