# Trigger Craft II

A Scenario GUI Editor in Python, for **Age of Empires 2 Definitive Edition**.

[AoE2TriggerCraft](https://github.com/MegaDusknoir/AoE2TriggerCraft) is the predecessor of this project.

一种基于 Python 的 帝国时代2决定版 场景编辑器。
[AoE2TriggerCraft](https://github.com/MegaDusknoir/AoE2TriggerCraft) 是该项目的前身。

## Usage

For general users, extract zip file and run

普通玩家可直接解压并运行

```
"Trigger Craft.exe"
```

## Getting Started

### Prerequisites
Install AoE2ScenarioParser
```
pip install AoE2ScenarioParser Pillow ttkbootstrap
```

### Preprocessing
Run
```
python prebuild.py
```

### Start
Run
```
python main.py
```

### Pack
Install pyinstaller
```
pip install pyinstaller
```

Run
```
python release.py
```

## License

[GNU General Public License v3.0](LICENSE)

## Acknowledgments

Powered by [AoE2ScenarioParser](https://github.com/KSneijders/AoE2ScenarioParser)