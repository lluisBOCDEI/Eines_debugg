#include <array>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

constexpr double PI = 3.14159265358979323846;

double lerp(double a, double b, double t){
    return (a + t*(b-a));
}

// Generate n equally spaced points on the unit circle
static std::vector<std::pair<double,double>> generate_input_vectors(int n) {
    std::vector<std::pair<double,double>> pts;
    if (n <= 0) return pts;
    pts.reserve(n);
    for (int k = 0; k < n; ++k) {
        double theta = 2.0 * PI * static_cast<double>(k) / static_cast<double>(n);
        double x = std::cos(theta);
        double y = std::sin(theta);
        pts.emplace_back(x, y);
    }
    return pts;
}

// Generate n equally spaced points on the unit circle
static std::vector<std::pair<double,double>> generate_input_forward_rotation(int n) {
    std::vector<std::pair<double,double>> pts;
    if (n <= 0) return pts;
    pts.reserve(n);
    for (int k = 0; k < n; ++k) {
        double theta = 2.0 * PI * static_cast<double>(k) / static_cast<double>(n);
        double x = 1.0;
        pts.emplace_back(x, theta);
    }
    return pts;
}

// Example function that maps (x,y) -> 4x1 vector
static std::array<double,4> compute_vector(double x, double y) {
    std::array<double,4> v;
    v[0] = x + y;
    v[1] = x - y;
    v[2] = x*x + y*y;       // should be 1.0 (unit circle), but shows the math
    v[3] = std::sin(x*y);
    return v;
}

// Read integer n from argv or stdin
static int read_n(int argc, char** argv) {
    if (argc > 1) {
        try { return std::stoi(argv[1]); }
        catch (...) {}
    }
    int n = 0;
    if (std::cin >> n) return n;
    return 0;
}

double normalize_angle(double angle){
    if (angle > 0.0 && angle > 2.0 * M_PI){
        return std::fmod(angle, 2.0 * M_PI) - 2.0 * M_PI;
    }
    else if (angle > 0.0)
    {
        return angle - 2.0 * M_PI;
    }
    else if (angle <= 0.0 && std::abs(angle) > 2.0 * M_PI)
    {
        return std::fmod(angle, 2.0 * M_PI);
    }
    else {
        return angle;
    }           
}

int get_quadrant(double angle){
    double angle_new = std::fmod(angle,-2.0*M_PI);
    if (angle_new >= -M_PI/2.0){
        return 1;
    }
    else if (angle_new >= -M_PI)
    {
        return 2;
    }
    else if (-3.0 * M_PI / 2.0)
    {
        return 3;
    }
    else if (angle_new >= -2.0 * M_PI)
    {
        return 4;
    }
    else{
        return 0;
    }
    
    
    
}

double alphas_tan(double alpha_1, double dist_1, double dist_2, double dist_4) {
    return std::atan((dist_4+dist_1)/(dist_1 /std::tan(alpha_1)));
}

std::vector<double> GetCommandsFromSpeedAndRotation(double front_command, double angular_command){

    double y_command = 0.0; double x_command = 0.0;

    std::vector<double> wheel_commands = {0.0,0.0,0.0,0.0};

    double alpha_theoretical = 0.0; double alpha_target= 0.0; 
    double left_wheel_command = 0.0; double right_wheel_command = 0.0;
    double caster_fork_command = 0.0; double caster_wheel_command = 0.0;  
    double x_dot_c_desired = 0.0; double y_dot_c_desired = 0.0;
    double axis_to_caster_distance = 1.75;
    double wheel_separation = 1.15; 
    double wheel_radius = 0.33;
    double caster_wheel_radius = 0.25;

    // Make sure speeds are within the limits:

    // Change to the equations frame:
    y_command = front_command;
    x_command = -double(angular_command) * axis_to_caster_distance;

    // Compute the desired values:
    alpha_theoretical = std::atan2(x_command,y_command);
    
    if (alpha_theoretical < -M_PI/2){
        alpha_target = alpha_theoretical + M_PI;
    } else if (alpha_theoretical > M_PI/2){
        alpha_target = alpha_theoretical - M_PI;
    } else {
        alpha_target = alpha_theoretical;
    }

    caster_fork_command = alpha_target;
    left_wheel_command = -(wheel_separation / (2.0 * wheel_radius))*double(angular_command) + (1.0/wheel_radius)*front_command;
    right_wheel_command = (wheel_separation / (2.0 * wheel_radius))*double(angular_command) + (1.0/wheel_radius)*front_command;

    caster_wheel_command =  std::cos(-alpha_theoretical+alpha_target)*std::sqrt(x_command*x_command + y_command*y_command)/caster_wheel_radius;

    // Now we limit also the output velocities:

    // LEFT WHEEL:
    wheel_commands[0] = left_wheel_command;

    // RIGHT WHEEL:
    wheel_commands[1] = right_wheel_command;

    // CASTER FORK:

    wheel_commands[2] = caster_fork_command;

    // CASTER WHEEL:

    wheel_commands[3] = caster_wheel_command;

    return wheel_commands;
}

std::vector<double> GetCommandsFromSpeedVector(double x_command, double y_command){

    std::vector<double> wheel_commands = {0.0,0.0,0.0,0.0,0.0,0.0};
    std::vector<double> velocities = {0.0,0.0,0.0,0.0}; // xdot, ydot , turretdot, basedot IDK if we are using this.

    double x_component = 0.0; double y_component = 0.0; double alpha_1 = 0.0; int quadrant = 0;
    double alpha_2= 0.0; double alpha_theoretical = 0.0; double left_wheel_command = 0.0; double right_wheel_command = 0.0;
    double caster_fork_command = 0.0; double caster_wheel_command = 0.0;  
    double x_dot_c_desired = 0.0; double y_dot_c_desired = 0.0; double alpha_target = 0.0; double alpha_c = 0.0;

    // Define values for the parameters:
    double max_x_velocity_ = 10.0; double min_x_velocity_ = -10.0; double max_y_velocity_ = 10.0; double min_y_velocity_ = -10.0;
    double center_distance_ = 1.0; double wheel_separation_ = 1.15; double center_to_caster_distance_ = 0.75;
    double left_wheel_radius_ = 0.750/2.0; double caster_fork_pos_ = 0.0; double caster_wheel_radius_ = 0.30;

    double unlim_left_wheel_cmd_ = 0.0; double unlim_right_wheel_cmd_ = 0.0; double unlim_caster_fork_cmd_ = 0.0; 
    double unlim_caster_wheel_cmd_ = 0.0; double min_left_wheel_motor_speed_ = -1000.00; double max_right_wheel_motor_speed_ = 1000.0; 
    double min_right_wheel_motor_speed_ = -1000.0; double max_caster_fork_motor_pos_ = 1000.0; double min_caster_fork_motor_pos_ = -1000.0;

    double max_caster_wheel_motor_speed_ = 1000.0; double min_caster_wheel_motor_speed_ = -1000.0;

    double max_left_wheel_motor_speed_ = 1000.0; 

    // Make speeds within the limits:
    if (x_command > max_x_velocity_ && x_command>0){
        x_command = max_x_velocity_;
    }else if(x_command < min_x_velocity_ && x_command<0){
        x_command = min_x_velocity_;
    }

    if (y_command > max_y_velocity_ && y_command>0){
        y_command = max_y_velocity_;
    }else if(y_command < min_y_velocity_ && y_command<0){
        y_command = min_y_velocity_;
    }
    
    // Compute the alpha theoretical:
    alpha_theoretical = std::atan2(y_command,x_command);

    // Compute the target alpha:

    if (alpha_theoretical < -M_PI/2){
        alpha_target = alpha_theoretical + M_PI;
    } else if (alpha_theoretical > M_PI/2){
        alpha_target = alpha_theoretical - M_PI;
    } else {
        alpha_target = alpha_theoretical;
    }

    caster_fork_command = alpha_target;
    left_wheel_command = -(wheel_separation_ / (2.0 * left_wheel_radius_ * center_distance_))*y_command + (1.0/left_wheel_radius_)*x_command;
    right_wheel_command = (wheel_separation_ / (2.0 * left_wheel_radius_ * center_distance_))*y_command + (1.0/left_wheel_radius_)*x_command;

    x_dot_c_desired = (left_wheel_radius_ * (center_distance_ + center_to_caster_distance_)/wheel_separation_)*left_wheel_command - (left_wheel_radius_ * (center_distance_ + center_to_caster_distance_)/wheel_separation_)*right_wheel_command;
    y_dot_c_desired = (left_wheel_radius_/2.0)*left_wheel_command + (left_wheel_radius_/2.0)*right_wheel_command;
    
    alpha_c = std::cos(alpha_theoretical-caster_fork_pos_) * std::sqrt(std::pow(x_dot_c_desired,2)+std::pow(y_dot_c_desired,2))/caster_wheel_radius_; // This nneed to take into account the caster wheel radius.

    caster_wheel_command = alpha_c;

    // Now we limit also the output velocities:
    unlim_left_wheel_cmd_ = left_wheel_command;
    unlim_right_wheel_cmd_ = right_wheel_command;
    unlim_caster_fork_cmd_ = caster_fork_command;
    unlim_caster_wheel_cmd_ = caster_wheel_command;

    // LEFT WHEEL:
    if (left_wheel_command > 0 && left_wheel_command > max_left_wheel_motor_speed_){
        wheel_commands[0] = max_left_wheel_motor_speed_;
    } else if (left_wheel_command < 0 && left_wheel_command < min_left_wheel_motor_speed_){
        wheel_commands[0] = min_left_wheel_motor_speed_;
    } else
    {
        wheel_commands[0] = left_wheel_command;
    }

    // RIGHT WHEEL:
    if (right_wheel_command > 0 && right_wheel_command > max_right_wheel_motor_speed_){
        wheel_commands[1] = max_right_wheel_motor_speed_;
    } else if (right_wheel_command < 0 && right_wheel_command < min_right_wheel_motor_speed_){
        wheel_commands[1] = min_right_wheel_motor_speed_;
    } else
    {
        wheel_commands[1] = right_wheel_command;
    }

    // CASTER FORK:

    quadrant = get_quadrant(caster_fork_command);

    if (quadrant == 4){
        caster_fork_command += 2.0 * M_PI;
    }
    

    if (caster_fork_command > 0 && caster_fork_command > max_caster_fork_motor_pos_){
        wheel_commands[2] = max_caster_fork_motor_pos_;
    }
    else if (caster_fork_command < 0 && caster_fork_command < min_caster_fork_motor_pos_)
    {
        wheel_commands[2] = min_caster_fork_motor_pos_;
    }
    else{
        wheel_commands[2] = caster_fork_command;
    }

    

    // CASTER WHEEL:
    // Compensate taking into account the limited velocity values:

    if (caster_wheel_command > 0 && caster_wheel_command > max_caster_wheel_motor_speed_){
        wheel_commands[3] = max_caster_wheel_motor_speed_;
    } else if (caster_wheel_command < 0 && caster_wheel_command < min_caster_wheel_motor_speed_){
        wheel_commands[3] = min_caster_wheel_motor_speed_;
    } else
    {
        wheel_commands[3] = caster_wheel_command;
    }
    
    wheel_commands[4] = alpha_theoretical;

    wheel_commands[5] = std::cos(alpha_theoretical-caster_fork_pos_);

    return wheel_commands;
}

std::vector<double> GetCommandsFromTrig(double velocitat, double gir){
    std::vector<double> wheel_commands = {0.0,0.0,0.0,0.0,0.0,0.0};
    double caster_fork_command = 0.0; double caster_wheel_command= 0.0; double left_wheel_command = 0.0; double right_wheel_command = 0.0;
    double angle = 0.0;
    double dist_roda_davant = 0.0; double dist_roda_trasera_dreta = 0.0; double dist_roda_trasera_esquerra = 0.0;
    double dist_punt_mig = 0.0;
    double factor_velocitat_roda_davantera = 0.0; double factor_velocitat_roda_trasera_dreta = 0.0;
    double factor_velocitat_roda_trasera_esquerra = 0.0; 
    const double DISTANCIA_EIX = 1.75; const double DISTANCIA_RODES = 1.15; const double EPSILON = 1e-3;
    const double RADI_CASTER = 0.25; const double RADI_RODA = 0.33;

    angle = lerp(0.0,M_PI,gir);

    if (std::abs(angle) < EPSILON){
        dist_roda_davant = DISTANCIA_EIX;
        dist_punt_mig = DISTANCIA_EIX;

        factor_velocitat_roda_davantera = 1.0;
        factor_velocitat_roda_trasera_esquerra = 1.0;
        factor_velocitat_roda_trasera_dreta = 1.0;
    }

    else {
        dist_punt_mig = DISTANCIA_EIX / std::tan(angle);
        dist_roda_davant = DISTANCIA_EIX / std::sin(angle);
        dist_roda_trasera_dreta = dist_punt_mig + (DISTANCIA_RODES/2.0);
        dist_roda_trasera_esquerra = dist_punt_mig - (DISTANCIA_RODES/2.0);

        factor_velocitat_roda_davantera = dist_roda_davant/dist_punt_mig;
        factor_velocitat_roda_trasera_esquerra = dist_roda_trasera_esquerra/dist_punt_mig;
        factor_velocitat_roda_trasera_dreta = dist_roda_trasera_dreta/dist_punt_mig;
    }

    // Tornem els valors de velocitat:

    caster_fork_command = angle;
    caster_wheel_command = velocitat * factor_velocitat_roda_davantera/RADI_CASTER;
    left_wheel_command = velocitat * factor_velocitat_roda_trasera_esquerra/RADI_RODA;
    right_wheel_command = velocitat * factor_velocitat_roda_trasera_dreta/RADI_RODA;

    wheel_commands[0] = left_wheel_command;
    wheel_commands[1] = right_wheel_command;
    wheel_commands[2] = caster_fork_command;
    wheel_commands[3] = caster_wheel_command;

    return wheel_commands;
}

std::vector<double> GetCommandsFromTrigVector(double forward_command, double angular_command){
    double x_command = 0.0; double y_command = 0.0; 
    
    std::vector<double> wheel_commands = {0.0,0.0,0.0,0.0,0.0,0.0};
    double caster_fork_command = 0.0; double caster_wheel_command= 0.0; double left_wheel_command = 0.0; double right_wheel_command = 0.0;
    double angle = 0.0;double alpha_theoretical = 0.0; double caster_fork_pos = 0.0;
    double dist_roda_davant = 0.0; double dist_roda_trasera_dreta = 0.0; double dist_roda_trasera_esquerra = 0.0;
    double dist_punt_mig = 0.0;
    double factor_velocitat_roda_davantera = 0.0; double factor_velocitat_roda_trasera_dreta = 0.0;
    double factor_velocitat_roda_trasera_esquerra = 0.0; 
    const double DISTANCIA_EIX = 1.75; const double DISTANCIA_RODES = 1.15; const double EPSILON = 1e-3;
    const double RADI_CASTER = 0.25; const double RADI_RODA = 0.33;

    y_command = forward_command;
    x_command = -angular_command*DISTANCIA_EIX;

    alpha_theoretical = std::atan2(x_command,y_command);

    if (alpha_theoretical < -M_PI/2){
        angle = alpha_theoretical + M_PI;
    } else if (alpha_theoretical > M_PI/2){
        angle = alpha_theoretical - M_PI;
    } else {
        angle = alpha_theoretical;
    }

    left_wheel_command = (DISTANCIA_RODES / (2.0 * RADI_RODA * DISTANCIA_EIX))*x_command + (1.0/RADI_RODA)*y_command;
    right_wheel_command = -(DISTANCIA_RODES / (2.0 * RADI_RODA * DISTANCIA_EIX))*x_command + (1.0/RADI_RODA)*y_command;
    caster_fork_command = angle;
    caster_wheel_command = std::cos(-alpha_theoretical+angle)*std::sqrt(x_command*x_command + y_command*y_command)/RADI_CASTER;

    wheel_commands[0] = left_wheel_command;
    wheel_commands[1] = right_wheel_command;
    wheel_commands[2] = caster_fork_command;
    wheel_commands[3] = caster_wheel_command;
    wheel_commands[4] = x_command;
    wheel_commands[5] = y_command;

    return wheel_commands;
}

int main(int argc, char** argv) {
    int n = read_n(argc, argv);
    if (n <= 0) {
        std::cerr << "Usage: " << argv[0] << " <n>\n";
        return 1;
    }

    auto pts = generate_input_forward_rotation(n);

    for (auto& p : pts) {
        auto v = GetCommandsFromSpeedAndRotation(p.first, p.second);
        auto w = GetCommandsFromTrigVector(p.first,p.second);
        std::cout << "(" << p.first << ", " << p.second << ") -> "
                  << "(Left command LL: " << v[0] << ", Right command LL: " << v[1] << ", Caster fork command LL: " 
                  << v[2] << ", Caster wheel command LL: " << v[3] << ")\n"
                  //<< v[2] << ", Caster wheel command: " << v[3] << ", Alpha Theoretical: " << v[4] << ", Caster wheel multiplyer: " << v[5] << ")\n";
                  << "(" << p.first << ", " << p.second << ") -> "
                  << "(Left command TRIG: " << w[0] << ", Right command TRIG: " << w[1] << ", Caster fork command TRIG: " 
                  << w[2] << ", Caster wheel command TRIG: " << w[3] << " X: " << w[4] << " Y: " << w[5] << ")\n";
    }

    return 0;
}
