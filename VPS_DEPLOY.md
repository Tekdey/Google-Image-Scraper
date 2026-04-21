# VPS_DEPLOY.md

Instructions pour l'agent Claude Code qui vient de `git clone` ce repo sur un VPS Linux fraîchement provisionné (Ubuntu/Debian). Le repo a déjà été modernisé (Selenium 4, Python 3.13, profil Chrome persistant, mode debugger-attach). Rien à patcher côté code — juste à provisionner la machine et démarrer.

## Contexte pour l'agent

- C'est un **proto**, pas de la prod. L'utilisateur accepte une maintenance manuelle occasionnelle (captcha à re-résoudre périodiquement).
- **Jamais de login Google** dans le profil Chrome du scraper. Si l'agent voit une suggestion d'auth Google n'importe où, la rejeter — c'est explicitement hors périmètre.
- Les IPs de datacenter (OVH, Hetzner, AWS, DO, etc.) sont connues de Google. Prévoir que le captcha tombera régulièrement. Ce n'est pas un bug à corriger — c'est le mode de fonctionnement attendu pour cette approche.
- Le volume visé est faible (< quelques dizaines d'images/jour). Si l'utilisateur monte le volume, signaler qu'il faudra passer à SerpAPI ou un proxy résidentiel.

## 1. Provisionner le système

```bash
sudo apt update
sudo apt install -y chromium-browser python3 python3-pip xvfb x11vnc git
pip3 install -r requirements.txt
```

Si `chromium-browser` n'est pas dispo (Debian récent), remplacer par `chromium` ou installer Chrome stable depuis `https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb`.

Vérifier : `chromium --version` (ou `google-chrome --version`) doit répondre.

## 2. Démarrer Chrome en daemon

Chrome doit **tourner en permanence** avec un port de debug ouvert. Le scraper s'y attache, donc un captcha résolu une fois reste valide tant que ce process vit.

```bash
# Écran X virtuel (Chrome refuse de démarrer sans DISPLAY)
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Chrome avec debug port + profil persistant
chromium \
  --remote-debugging-port=9222 \
  --user-data-dir="$PWD/chrome-profile" \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-blink-features=AutomationControlled \
  --lang=fr-FR \
  --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36" \
  > /tmp/chrome.log 2>&1 &
```

Pour pérenniser entre les déconnexions SSH : lancer sous `tmux`/`screen`, ou créer un service systemd. Ne pas utiliser `nohup` seul — le process enfant Chrome peut mourir quand le shell de login ferme.

## 3. Résoudre le captcha initial (au choix)

### Option A — Pré-chauffage local (recommandé pour démarrer)

Sur la machine locale de l'utilisateur, lancer `main.py` en headful, résoudre le captcha, puis `rsync -avz chrome-profile/ user@vps:$PWD/chrome-profile/`. Redémarrer Chrome sur le VPS pour qu'il reprenne le profil.

### Option B — VNC sur le VPS

```bash
x11vnc -display :99 -passwd UN_MDP_COMPLEXE -forever -rfbport 5900 &
```

L'utilisateur se connecte avec un client VNC (RealVNC, TigerVNC) sur `<ip-vps>:5900`, voit l'écran virtuel, clique sur le captcha dans Chrome. **Ouvrir le port 5900 uniquement sur IP source de l'utilisateur** (UFW ou security group), jamais `0.0.0.0`.

## 4. Configurer `main.py`

Deux paramètres à changer vs la config par défaut :

```python
headless = True                                # obligatoire sur VPS, pas de GUI
debugger_address = "127.0.0.1:9222"            # attache au Chrome lancé à l'étape 2
```

Laisser `number_of_workers = 1` tant qu'on partage un seul Chrome. Ajuster `search_keys`, `number_of_images`, `min_resolution`/`max_resolution` selon le besoin.

## 5. Lancer le scraper

```bash
python3 main.py
```

Les images sortent dans `./photos/<search_key>/`. Le scraper **ne ferme pas** le Chrome daemon à la fin (c'est géré par `owns_driver = False` quand `debugger_address` est set) — on peut relancer `python3 main.py` autant de fois que nécessaire.

## 6. Signaux à surveiller

- **0 image récupérée, "Unable to get link" en boucle** → captcha ou Chrome redirigé vers `/sorry/index`. Re-résoudre (Option A ou B), puis relancer.
- **Erreur `cannot connect to chrome at 127.0.0.1:9222`** → le daemon Chrome est mort. Relancer l'étape 2.
- **`chromedriver version mismatch`** → `patch.py` est supposé ré-télécharger la bonne version via regex sur le message d'erreur. Si ça boucle, supprimer `webdriver/chromedriver` et relancer — Selenium Manager (inclus dans Selenium 4.6+) prendra le relais.
- **Google recaptchaise après N requêtes** → normal. Baisser la cadence (ajouter `time.sleep(5)` entre search_keys), ou accepter de re-résoudre.

## 7. Ce que l'agent ne doit PAS faire

- Ajouter un login Google (cf. contexte).
- Retirer les flags anti-détection en pensant "simplifier".
- Passer `number_of_workers > 1` avec un profil unique — Chrome locke `user-data-dir` en accès concurrent, les workers crasheront.
- Committer le dossier `chrome-profile/` (déjà dans `.gitignore`). Il contient potentiellement des cookies de session.
- Committer des images téléchargées dans `photos/` (déjà ignoré).

## 8. Pour aller plus loin (si le proto devient sérieux)

- **SerpAPI** (~$50/mois, 5k requêtes) remplace tout Selenium par un `requests.get` à `https://serpapi.com/search?engine=google_images&q=...` — zéro captcha.
- **Proxy résidentiel** (Bright Data, IPRoyal) — garde Selenium mais avec IP non-flaggée.
- **`undetected-chromedriver`** — drop-in remplacement du driver actuel, plus furtif. Utile en combo avec les proxies.

Ces chemins demandent des décisions côté utilisateur (budget, ToS) — ne pas les implémenter sans accord explicite.
