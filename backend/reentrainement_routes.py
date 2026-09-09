import os
import sys
import threading
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/reentrainement", tags=["Réentraînement"])

_state_lock = threading.Lock()
_state = {
    "en_cours": False,
    "pourcentage": 0,
    "epoch_actuelle": 0,
    "epoch_totale": 15,
    "message_statut": "Inactif",
    "erreur": None,
}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _get_statut():
    with _state_lock:
        return dict(_state)


def _update_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)


def _progress_callback(pourcentage, message_statut, epoch_actuelle=0, epoch_totale=15):
    _update_state(
        pourcentage=min(100, max(0, int(pourcentage))),
        message_statut=message_statut,
        epoch_actuelle=epoch_actuelle,
        epoch_totale=epoch_totale,
    )


def _executer_reentrainement(user_name: str, user_role: str):
    original_cwd = os.getcwd()
    try:
        os.chdir(PROJECT_ROOT)
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

        _update_state(
            en_cours=True,
            pourcentage=0,
            epoch_actuelle=0,
            epoch_totale=15,
            message_statut="Initialisation du réentraînement...",
            erreur=None,
        )

        from classification.reentrainement import run_reentrainement

        run_reentrainement(progress_callback=_progress_callback)

        _update_state(
            en_cours=False,
            pourcentage=100,
            message_statut="Réentraînement terminé avec succès.",
            erreur=None,
        )
        _log_action(
            user_name, user_role,
            "Réentraînement et déploiement du classificateur terminés avec succès.",
        )
    except Exception as e:
        _update_state(
            en_cours=False,
            message_statut=f"Échec du réentraînement : {e}",
            erreur=str(e),
        )
        _log_action(user_name, user_role, f"Échec : {e}")
    finally:
        os.chdir(original_cwd)


def _log_action(user_name: str, user_role: str, detail: str):
    from datetime import datetime
    from backend.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute("""
    INSERT INTO logs (date_heure, utilisateur, role, action, element_concerne, detail)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (now_str, user_name, user_role, "Réentraînement IA", "Modèle XLM-RoBERTa", detail))
    conn.commit()
    conn.close()


@router.get("/statut")
def get_reentrainement_statut():
    return _get_statut()


@router.post("/lancer")
def lancer_reentrainement(
    user_name: str = Query(...),
    user_role: str = Query(...),
):
    if user_role != "Administrateur":
        raise HTTPException(status_code=403, detail="Seul un administrateur peut lancer le réentraînement.")

    statut = _get_statut()
    if statut["en_cours"]:
        raise HTTPException(status_code=409, detail="Un réentraînement est déjà en cours.")

    thread = threading.Thread(
        target=_executer_reentrainement,
        args=(user_name, user_role),
        daemon=True,
    )
    thread.start()

    return {"message": "Réentraînement lancé en arrière-plan."}
