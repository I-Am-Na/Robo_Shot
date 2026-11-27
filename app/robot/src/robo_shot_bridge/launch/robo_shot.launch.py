"""중간 연결 노드 + 주유 액션 서버(시뮬레이션) 실행.

ros2 launch robo_shot_bridge robo_shot.launch.py server_url:=http://localhost:8000 step_seconds:=1.0
실제 로봇 액션 서버를 따로 띄울 때는 use_sim_robot:=false
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    server_url = LaunchConfiguration("server_url")
    poll_interval = LaunchConfiguration("poll_interval")
    step_seconds = LaunchConfiguration("step_seconds")
    use_sim_robot = LaunchConfiguration("use_sim_robot")

    return LaunchDescription([
        DeclareLaunchArgument("server_url", default_value="http://localhost:8000"),
        DeclareLaunchArgument("poll_interval", default_value="2.0"),
        DeclareLaunchArgument("step_seconds", default_value="1.0"),
        DeclareLaunchArgument("use_sim_robot", default_value="true"),
        Node(
            package="robo_shot_bridge",
            executable="server_bridge",
            name="server_bridge",
            output="screen",
            parameters=[{"server_url": server_url, "poll_interval": poll_interval}],
        ),
        Node(
            package="robo_shot_bridge",
            executable="fueling_action_server",
            name="fueling_action_server",
            output="screen",
            parameters=[{"step_seconds": step_seconds}],
            condition=IfCondition(use_sim_robot),
        ),
    ])
