#include <array>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

constexpr double PI = 3.14159265358979323846;

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

    if (angle_new >= 0 && angle_new < M_PI/2.0){
        return 1;
    }
    else if (angle_new >= M_PI/2.0 && angle_new < M_PI)
    {
        return 2;
    }
    else if (angle_new >= M_PI && angle_new < 3.0*M_PI/2.0)
    {
        return 3;
    }
    else if (angle_new >= 3.0*M_PI/2.0 && angle_new <= 2.0*M_PI) {
        return 4;
    }
    else if (angle_new <= 0 && angle_new > -M_PI/2.0){
        return 4;
    }
    else if (angle_new < -M_PI/2.0 && angle_new > -M_PI){
        return 3;
    }
    else if (angle_new < -M_PI && angle_new > -3.0*M_PI/2.0){
        return 2;
    }
    else if (angle_new < -3.0*M_PI/2.0 && angle_new > -2.0*M_PI){
        return 1;
    }
    else{
        return 0;
    }   
}

double alphas_tan(double alpha_1, double dist_1, double dist_2, double dist_4) {
    return std::atan((dist_4+dist_1)/(dist_1 /std::tan(alpha_1)));
}

std::vector<double> GetCommandsFromSpeedVector(double x_command, double y_command){

    std::vector<double> wheel_commands = {0.0,0.0,0.0,0.0,0.0,0.0};
    std::vector<double> velocities = {0.0,0.0,0.0,0.0}; // xdot, ydot , turretdot, basedot IDK if we are using this.

    double x_component = 0.0; double y_component = 0.0; double alpha_1 = 0.0; int quadrant = 0;
    double alpha_2= 0.0; double beta_d = 0.0; double left_wheel_command = 0.0; double right_wheel_command = 0.0;
    double caster_fork_command = 0.0; double caster_wheel_command = 0.0;  
    double x_dot_c_desired = 0.0; double y_dot_c_desired = 0.0; double alpha_target = 0.0; double alpha_c = 0.0;

    // Define values for the parameters:
    double max_x_velocity_ = 10.0; double min_x_velocity_ = -10.0; double max_y_velocity_ = 10.0; double min_y_velocity_ = -10.0;
    double center_distance_ = 1.0; double wheel_separation_ = 1.15; double center_to_caster_distance_ = 0.75;
    double left_wheel_radius_ = 0.750/2.0; double caster_fork_pos_ = 0.0; 

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

    alpha_1 = std::atan2(y_command,x_command) - (M_PI/2.0);
    alpha_1 = normalize_angle(alpha_1);
    quadrant = get_quadrant(alpha_1);

    

    switch (quadrant) // I think thatt this quadrant function may be irrelevant.
    {
    case 1:
        alpha_2 = alphas_tan(alpha_1,center_distance_,wheel_separation_,center_to_caster_distance_);
        alpha_target = alpha_2;
        break;
    case 2:
        alpha_2 = alphas_tan(alpha_1,center_distance_,wheel_separation_,center_to_caster_distance_) - M_PI;
        alpha_target = alpha_2 - M_PI;
        break;
    case 3:
        alpha_2 = alphas_tan(alpha_1,center_distance_,wheel_separation_,center_to_caster_distance_) - M_PI;
        alpha_target = alpha_2 + M_PI;
        break;
    case 4:
        alpha_2 = alphas_tan(alpha_1,center_distance_,wheel_separation_,center_to_caster_distance_)-(2.0*M_PI);
        alpha_target = alpha_2;
        break;
    
    default:
        alpha_target = alpha_2;
        break;
    }

    alpha_2 = normalize_angle(alpha_2);
    alpha_target = normalize_angle(alphas_tan(alpha_1,center_distance_,wheel_separation_,center_to_caster_distance_));

    beta_d = alpha_2;
    caster_fork_command = alpha_target;
    left_wheel_command = (wheel_separation_ / (2.0 * left_wheel_radius_ * center_distance_))*x_command + (1.0/left_wheel_radius_)*y_command;
    right_wheel_command = -(wheel_separation_ / (2.0 * left_wheel_radius_ * center_distance_))*x_command + (1.0/left_wheel_radius_)*y_command;

    x_dot_c_desired = (left_wheel_radius_ * (center_distance_ + center_to_caster_distance_)/wheel_separation_)*left_wheel_command - (left_wheel_radius_ * (center_distance_ + center_to_caster_distance_)/wheel_separation_)*right_wheel_command;
    y_dot_c_desired = (left_wheel_radius_/2.0)*left_wheel_command + (left_wheel_radius_/2.0)*right_wheel_command;
    
    alpha_c = std::cos(beta_d-caster_fork_pos_) * std::sqrt(std::pow(x_dot_c_desired,2)+std::pow(y_dot_c_desired,2)); // This nneed to take into account the caster wheel radius.

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
    
    wheel_commands[4] = double(get_quadrant(caster_fork_command));

    wheel_commands[5] = std::fmod(caster_fork_command,-2.0*M_PI);;

    return wheel_commands;
}

int main(int argc, char** argv) {
    int n = read_n(argc, argv);
    if (n <= 0) {
        std::cerr << "Usage: " << argv[0] << " <n>\n";
        return 1;
    }

    auto pts = generate_input_vectors(n);

    for (auto& p : pts) {
        auto v = GetCommandsFromSpeedVector(p.first, p.second);
        std::cout << "(" << p.first << ", " << p.second << ") -> "
                  << "(" << v[0] << ", " << v[1] << ", " 
                  << v[2] << ", " << v[3] << ", " << v[4] << ", " << v[5] << ")\n";
    }

    return 0;
}
