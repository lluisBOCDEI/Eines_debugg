from numpy import interp, pi, tan, radians, sin
import math
import os
import pandas as pd
import matplotlib.pyplot as plt  # <-- added for plotting

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

    # Compute wheel speeds (RPM-like per your base)
    velocitat_roda_devantera = velocitat * factor_velocitat_roda_devantera / CIRCUNFERENCIA_RODA_DELANTERA 
    velocitat_roda_trasera_dreta = velocitat * factor_velocitat_roda_trasera_dreta / CIRCUNFERENCIA_RODA_TRASERA 
    velocitat_roda_trasera_esquerra = velocitat * factor_velocitat_roda_trasera_esquerra / CIRCUNFERENCIA_RODA_TRASERA 

    return (
        velocitat_roda_trasera_esquerra,
        velocitat_roda_trasera_dreta,
        gir,
        velocitat_roda_devantera
    )


class PlotGenerator():
    # -------- EDIT THESE if you want different columns in the plots ----------
    PLOT_TIME_COL = "time"
    # Three row pairs: (solid_series, dashed_series, title)
    PLOT_PAIRS = [
        ("Rad/s_Esq",  "left_motor_unlimited_command",   "Left Motor: command vs unlimited"),
        ("Rad/s_Dret", "right_motor_unlimited_command",  "Right Motor: command vs unlimited"),
        ("Rad/s_Devant","caster_wheel_motor_unlimited_command", "Caster Wheel: command vs unlimited"),
        ("Angle","caster_fork_target","Caster Fork: command vs trigonometria"),
    ]
    # ------------------------------------------------------------------------

    def __init__(self):
        super().__init__()
        self.package_directory = os.path.expanduser("~/Desktop/test_stuff")
        self.excel_file_path = os.path.join(self.package_directory, 'sample_data', 'demo_comandament.xlsx')
        self.data = self.load_data(self.excel_file_path)
        self.apply_motor_function()     # keep your existing computation
        self.plot_comparisons()         # NEW: make the 4-row comparison plot

    def load_data(self, file_name: str):
        loaded_data = pd.read_excel(self.excel_file_path, index_col=0)
        print('✅ Successfully loaded data!')
        return loaded_data

    def apply_motor_function(self):
        DISTANCIA_EIX = 1.75
        # Change these to the correct column names from your Excel file:
        velocity_col = "x_command_mando"         # example
        steering_col = "angular_command_mando"   # example

        x_command = self.data[velocity_col].to_list()
        angular_command = self.data[steering_col].to_list()

        results = []
        for x_c, ang_c in zip(x_command, angular_command):
            v = x_c
            g = -ang_c * pi/2.0
            rpm_left, rpm_right, angle, rpm_front = mouMotors_3(v, g)
            results.append((rpm_left, rpm_right, angle, rpm_front))

        # Add results as new columns
        rpm_df = pd.DataFrame(results, columns=["Rad/s_Esq", "Rad/s_Dret", "Angle", "Rad/s_Devant"], index=self.data.index)
        self.data = pd.concat([self.data, rpm_df], axis=1)

        # Show preview
        print("✅ Computed Rad/s values:")
        print(self.data[["Rad/s_Esq", "Rad/s_Dret","Angle", "Rad/s_Devant"]].head())

        # Save to Excel (kept as in your base)
        out_file = os.path.join(self.package_directory, 'sample_data', 'exemple_with_rpm_2.xlsx')
        self.data.to_excel(out_file, index=False)
        print(f"💾 Results saved to {out_file}")

    def plot_comparisons(self):
        """
        Make a figure with 3 rows. Each row overlays TWO series vs time:
        - first series: solid line
        - second series: dashed line
        """
        # Check required columns
        cols_needed = [self.PLOT_TIME_COL] + [c for pair in self.PLOT_PAIRS for c in pair[:2]]
        missing = [c for c in cols_needed if c not in self.data.columns]
        if missing:
            print(f"⚠️ Missing columns for plotting: {missing}")
            print("   Available columns:", list(self.data.columns))
            return

        t = self.data[self.PLOT_TIME_COL].to_numpy()

        fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(12, 9), sharex=True)
        for ax, (solid_col, dashed_col, title) in zip(axes, self.PLOT_PAIRS):
            y1 = self.data[solid_col].to_numpy()
            y2 = self.data[dashed_col].to_numpy()

            ax.plot(t, y1, linestyle='-',  label=solid_col)
            ax.plot(t, y2, linestyle='--', label=dashed_col)
            ax.set_title(title)
            ax.grid(True, which='both', linestyle=':')
            ax.legend(loc='best')

        axes[-1].set_xlabel("time")
        fig.tight_layout()

        # Save the figure next to your data
        plot_path = os.path.join(self.package_directory, 'sample_data', 'compare_over_time.png')
        fig.savefig(plot_path, dpi=150)
        print(f"🖼️ Plot saved to: {plot_path}")
        plt.show()


def main():
    plot_generator = PlotGenerator()

if __name__ == '__main__':
    raise SystemExit(main())
