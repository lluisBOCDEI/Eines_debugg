from numpy import interp, pi, tan, radians, sin
import math
import os
import pandas as pd

def mouMotors_3(velocitat, gir, rot_gir = 0):
    # Distancia entre l'eix de les rodes
    DISTANCIA_EIX = 1.75
    DISTANCIA_RODES = 1.15
    RADI_RODA_DELANTERA = 0.25
    RADI_RODA_TRASERA = 0.33
    CIRCUNFERENCIA_RODA_DELANTERA = RADI_RODA_DELANTERA
    CIRCUNFERENCIA_RODA_TRASERA = RADI_RODA_TRASERA

    #angle = interp(gir, [-1, 1], [-90, +90])  # map normalized steering
    if gir == 0:
        dist_roda_devantera = DISTANCIA_EIX
        distancia_punt_mig = DISTANCIA_EIX
        distancia_roda_trasera_dreta = DISTANCIA_EIX
        distancia_roda_trasera_esquerra = DISTANCIA_EIX
    else:
        distancia_punt_mig = DISTANCIA_EIX / tan(gir)
        dist_roda_devantera = DISTANCIA_EIX / sin(gir)
        distancia_roda_trasera_dreta = distancia_punt_mig - DISTANCIA_RODES / 2
        distancia_roda_trasera_esquerra = distancia_punt_mig + DISTANCIA_RODES / 2

    if gir == 0:
        factor_velocitat_roda_devantera = 1
        factor_velocitat_roda_trasera_dreta = 1
        factor_velocitat_roda_trasera_esquerra = 1
    else:
        factor_velocitat_roda_devantera = 1
        factor_velocitat_roda_trasera_dreta = distancia_roda_trasera_dreta / dist_roda_devantera
        factor_velocitat_roda_trasera_esquerra = distancia_roda_trasera_esquerra / dist_roda_devantera

    # Compute wheel speeds in RPM (no scaling)
    velocitat_roda_devantera = velocitat * factor_velocitat_roda_devantera / CIRCUNFERENCIA_RODA_DELANTERA 
    velocitat_roda_trasera_dreta = velocitat * factor_velocitat_roda_trasera_dreta / CIRCUNFERENCIA_RODA_TRASERA 
    velocitat_roda_trasera_esquerra = velocitat * factor_velocitat_roda_trasera_esquerra / CIRCUNFERENCIA_RODA_TRASERA 

    return (
        velocitat_roda_trasera_esquerra,
        velocitat_roda_trasera_dreta,
        velocitat_roda_devantera
        #distancia_punt_mig,
        #dist_roda_devantera,
        #distancia_roda_trasera_dreta
    )


class PlotGenerator():
    def __init__(self):
        super().__init__()
        self.package_directory = os.path.expanduser("~/Desktop/test_stuff")
        self.excel_file_path = os.path.join(self.package_directory, 'sample_data', 'exemple.xlsx')
        self.data = self.load_data(self.excel_file_path)
        self.apply_motor_function()

    def load_data(self, file_name: str):
        loaded_data = pd.read_excel(self.excel_file_path, index_col=0)
        print('✅ Successfully loaded data!')
        return loaded_data

    def apply_motor_function(self):
        """
        Applies mouMotors_3 to each row using two chosen columns from the Excel.
        Stores RPM results into three new columns in the dataframe.
        """
        DISTANCIA_EIX = 1.75
        # Change these to the correct column names from your Excel file:
        velocity_col = "x_command_mando"   # example
        steering_col = "angular_command_mando"  # example

        x_command = self.data[velocity_col].to_list()
        angular_command = self.data[steering_col].to_list()

        results = []
        for x_c, ang_c in zip(x_command, angular_command):
            v = math.sqrt(x_c**2+ (ang_c*DISTANCIA_EIX)**2)
            g = (pi/2.0)-math.atan2(x_c,ang_c*DISTANCIA_EIX)
            rpm_left, rpm_right, rpm_front = mouMotors_3(v, g)
            results.append((rpm_left, rpm_right, rpm_front))
            #results.append((v, g, interp(g, [-1, 1], [-90, +90])))

        # Add results as new columns
        rpm_df = pd.DataFrame(results, columns=["RPM_Esq", "RPM_Dret", "RPM_Devant"], index=self.data.index)
        self.data = pd.concat([self.data, rpm_df], axis=1)

        # Show preview
        print("✅ Computed RPM values:")
        print(self.data[["RPM_Esq", "RPM_Dret", "RPM_Devant"]].head())

        # Save to Excel
        out_file = os.path.join(self.package_directory, 'sample_data', 'exemple_with_rpm.xlsx')
        self.data.to_excel(out_file, index=False)
        print(f"💾 Results saved to {out_file}")


def main():
    plot_generator = PlotGenerator()

if __name__ == '__main__':
    raise SystemExit(main())
