from numpy import interp, pi, tan, radians, sin, cos
import os
import pandas as pd

def mouMotors_3(velocitat, gir, rot_gir=0):
    # Distancia entre l'eix de les rodes
    DISTANCIA_EIX = 1.75
    DISTANCIA_RODES = 1.15
    RADI_RODA_DELANTERA = 0.25
    RADI_RODA_TRASERA_DRETA = 0.33
    CIRCUNFERENCIA_RODA_DELANTERA = 2.0 * pi * RADI_RODA_DELANTERA
    CIRCUNFERENCIA_RODA_TRASERA = 2.0 * pi * RADI_RODA_TRASERA_DRETA

    angle = interp(gir, [-pi, pi], [-90, +90])
    if angle == 0.0:
        dist_roda_devantera = DISTANCIA_EIX
        distancia_punt_mig = DISTANCIA_EIX
    else:
        distancia_punt_mig = DISTANCIA_EIX / tan(radians(angle))
        dist_roda_devantera = DISTANCIA_EIX / sin(radians(angle))
        distancia_roda_trasera_dreta = distancia_punt_mig - DISTANCIA_RODES / 2.0
        distancia_roda_trasera_esquerra = distancia_punt_mig + DISTANCIA_RODES / 2.0

    if angle == 0.0:
        factor_velocitat_roda_devantera = 1.0
        factor_velocitat_roda_trasera_dreta = 1.0
        factor_velocitat_roda_trasera_esquerra = 1.0
    else:
        factor_velocitat_roda_devantera = dist_roda_devantera / distancia_punt_mig
        factor_velocitat_roda_trasera_dreta = distancia_roda_trasera_dreta / distancia_punt_mig
        factor_velocitat_roda_trasera_esquerra = distancia_roda_trasera_esquerra / distancia_punt_mig

    # compute wheel speeds (rpm)
    velocitat_roda_devantera = velocitat * factor_velocitat_roda_devantera / CIRCUNFERENCIA_RODA_DELANTERA * 60
    velocitat_roda_trasera_dreta = velocitat * factor_velocitat_roda_trasera_dreta / CIRCUNFERENCIA_RODA_TRASERA * 60
    velocitat_roda_trasera_esquerra = velocitat * factor_velocitat_roda_trasera_esquerra / CIRCUNFERENCIA_RODA_TRASERA * 60

    return velocitat_roda_trasera_esquerra, velocitat_roda_trasera_dreta, velocitat_roda_devantera

print(mouMotors_3(0.0099983219,1))