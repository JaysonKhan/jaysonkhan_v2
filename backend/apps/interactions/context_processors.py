from interactions.views import get_tg_profile

def tg_profile(request):
    """
    Ensures 'tg_profile' is available in all templates.
    """
    profile = get_tg_profile(request)
    return {
        'tg_profile': profile
    }
