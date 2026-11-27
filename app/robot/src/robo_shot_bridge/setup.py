from glob import glob

from setuptools import find_packages, setup

package_name = "robo_shot_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Robo_Shot",
    maintainer_email="dev@robo-shot.local",
    description="Robo_Shot server <-> fueling robot bridge",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "server_bridge = robo_shot_bridge.server_bridge_node:main",
            "fueling_action_server = robo_shot_bridge.fueling_action_server:main",
        ],
    },
)
