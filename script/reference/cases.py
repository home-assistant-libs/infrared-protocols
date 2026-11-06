"""Reference inputs and independently specified observable state for each family."""

from itertools import product

MODES = {0: "off", 1: "auto", 2: "cool", 3: "heat", 4: "fan_only", 5: "dry", 6: "auto"}
FANS = {2: "auto", 3: "low", 4: "medium", 5: "high"}
SWINGS = {0: "off", 1: "both", 2: "vertical", 3: "horizontal"}
FACTORIES = {
    "ballu": "BalluCommand",
    "delonghi": "DelonghiCommand",
    "tcl112": "Tcl112Command",
    "zhlt01": "Zhlt01Command",
    "whynter": "WhynterCommand",
    "remko_ar715": "RemkoAr715Command",
    "islandaire": "IslandaireCommand",
    "mistral_ir": "MistralCommand",
    "daikin_arc": "DaikinArcCommand",
    "daikin_brc": "DaikinBrcCommand",
    "haier_tundra": "HaierTundraCommand",
    "airton": "AirtonCommand",
    "friedrich": "FriedrichCommand",
    "mitsubishi": "MitsubishiCommand",
    "noblex": "NoblexCommand",
    "hitachi_ac344": "HitachiAc344Command",
    "hitachi_ac424": "HitachiAc424Command",
    "whirlpool": "WhirlpoolCommand",
    "emmeti": "EmmetiCommand",
    "pd_pioneer_ir": "PdPioneerClimateCommand",
    "toshiba_0": "ToshibaCommand.climate",
    "toshiba_1": "ToshibaRacCommand.climate",
    "toshiba_2": "ToshibaRacCommand.climate",
    "toshiba_3": "ToshibaRas2819Command.climate",
    "toshiba_4": "ToshibaSeiyaCommand.climate",
    "toshiba_5": "ToshibaRasB10n3kv2Command.climate",
}
GREE = ("generic", "yan", "yaa", "yac", "yac1fb9", "yb1fa", "yx1ff", "yag", "yaw1f")
FACTORIES.update({f"gree_{i}": "GreeModelCommand" for i in range(9)})


def temperatures(component, mode):
    """Cover each native range, a normal setpoint, and supported half degrees."""
    if component == "delonghi":
        return (13, 24, 27) if mode == 3 else (17, 24, 32)
    if component == "friedrich":
        return (60 if mode == 3 else 64, 72, 88)
    if component == "islandaire":
        return (61, 72, 88)
    if component == "daikin_arc":
        return (10, 24, 24.5, 30)
    if component == "daikin_brc":
        return (16, 24, 32)
    if component in ("tcl112", "pd_pioneer_ir"):
        return (16, 24, 24.5, 31)
    if component == "mitsubishi":
        return (16, 24, 31)
    if component == "toshiba_3":
        return (18, 24, 25, 30)
    if component in ("toshiba_1", "toshiba_2"):
        return (16, 24, 30)
    if component.startswith("toshiba"):
        return (17, 24, 25, 30)
    if component in ("ballu", "zhlt01", "hitachi_ac344", "hitachi_ac424"):
        return (16, 24, 32)
    if component == "whirlpool":
        return (18, 24, 32)
    if component == "whynter":
        return (16, 24, 32)
    if component == "airton":
        return (16, 24, 31)
    return (16, 24, 30)


def arguments(component, mode, fan, temperature, swing):
    """Select supported remote inputs, with explicit upstream transmitter exceptions."""
    # AUTO and HEAT_COOL are distinct upstream inputs. Only Ballu and ZHLT01
    # implement AUTO; the remaining encoders use HEAT_COOL for their auto program.
    if mode == 6 and component not in ("ballu", "zhlt01"):
        return None
    vertical, horizontal = swing in (1, 2), swing in (1, 3)
    power = mode != 0
    args = dict(
        mode=MODES[mode] if power else "cool",
        fan=FANS[fan],
        temperature=temperature,
        power=power,
    )
    factory = FACTORIES[component]
    both = {
        "ballu",
        "zhlt01",
        "daikin_arc",
        "haier_tundra",
        "mitsubishi",
        "pd_pioneer_ir",
    }
    vertical_only = {"tcl112", "remko_ar715", "friedrich", "noblex", "emmeti"}
    if component.startswith("gree_"):
        model = GREE[int(component[-1])]
        args["model"] = model
        if model in ("yac", "yag", "yaw1f"):
            both.add(component)
        elif model != "generic":
            vertical_only.add(component)
    if component in both:
        args.update(swing_v=vertical, swing_h=horizontal)
    elif component in vertical_only:
        if horizontal:
            return None
        args["swing_v"] = vertical
    elif component == "daikin_brc":
        if swing not in (0, 1) or fan == 2:
            return None
        args["swing"] = bool(swing)
    elif component.startswith("hitachi"):
        if mode == 1 or mode == 4 and fan == 2 or mode == 5 and fan > 3:
            return None
        if component == "hitachi_ac344" and mode == 0:
            return (
                None  # Its upstream fresh-object off path retains an unrelated state.
            )
        args.update(swing_v=vertical, horizontal_position=0 if horizontal else 3)
        if component == "hitachi_ac344" and vertical:
            args["button"] = 129
    elif component == "toshiba_4":
        if not power and fan != 2:
            return None
        args["swing_code"] = {0: 23, 1: 1, 2: 8, 3: 9}[swing]
    elif swing:
        return None
    if component == "whynter" and (mode == 1 or fan == 2):
        return None
    if component == "remko_ar715" and (mode in (1, 3) or mode in (4, 5) and fan != 2):
        return None
    if component == "islandaire" and (mode in (1, 5) or fan == 4):
        return None
    if component == "haier_tundra" and not power and vertical:
        return None
    if component == "airton" and not power:
        args["mode"] = "auto"
    if component == "daikin_arc":
        args.update(humidity=40, humidity_changed=power)
    if component == "friedrich":
        args.pop("power")
        if not power:
            if fan != 2 or swing or temperature != 72:
                return None
            return "FriedrichUtilityCommand", {"button": 64}
    if component == "mitsubishi":
        args.pop("fan")
        args["native_fan"] = fan - 2
        if not power:
            args["mode"] = "heat"
    if component == "noblex" and mode not in (0, 2, 4):
        return None  # Upstream ORs mode into a cool template; independent mode tests cover this.
    if component == "whirlpool":
        args.pop("power")
        args.update(power_toggle=power, off_command=not power)
    if component in ("toshiba_1", "toshiba_2", "toshiba_3"):
        args.pop("power")
        if mode in (0, 1, 5) and fan != 2:
            return None
        if not power:
            return factory.replace("climate", "power_off"), {}
        if component == "toshiba_2":
            args.update(temperature=round(temperature * 9 / 5 + 32), fahrenheit=True)
    if component == "emmeti":
        args["blade"] = int(args.pop("swing_v"))
        if not power and (fan != 2 or swing):
            return None
    return factory, args


def cases():
    """Emit input cases directly; fixtures are output, never an input manifest."""
    result = []
    for component in FACTORIES:
        for mode, fan, swing in product(MODES, FANS, SWINGS):
            for temperature in temperatures(component, mode):
                selected = arguments(component, mode, fan, temperature, swing)
                if selected is None:
                    continue
                factory, args = selected
                key = f"{component}:{'heat_cool' if mode == 1 else MODES[mode]}:{FANS[fan]}:{temperature}:{SWINGS[swing]}"
                result.append(
                    dict(
                        key=key,
                        component=component,
                        mode=mode,
                        fan=fan,
                        temperature=temperature,
                        swing=swing,
                        factory=factory,
                        arguments=args,
                    )
                )

    def extra(
        key,
        component,
        factory,
        args,
        *,
        mode=2,
        fan=2,
        temperature=24,
        swing=0,
        setup="",
        invoke="obj.transmit_state();",
    ):
        result.append(
            dict(
                key=key,
                component=component,
                mode=mode,
                fan=fan,
                temperature=temperature,
                swing=swing,
                factory=factory,
                arguments=args,
                setup=setup,
                invoke=invoke,
            )
        )

    extra(
        "airton:off-after-cool",
        "airton",
        "AirtonCommand",
        dict(mode="cool", temperature=24, power=False),
        mode=0,
        setup="obj.previous_mode_=1;",
    )
    extra(
        "daikin_arc:humidity-unchanged",
        "daikin_arc",
        "DaikinArcCommand",
        dict(mode="cool", temperature=24, humidity=40, humidity_changed=False),
        setup="obj.last_humidity_=40;",
    )
    for preset, wire in (
        ("econo_cool", "ECO"),
        ("night", "SLEEP"),
        ("powerful", "BOOST"),
    ):
        extra(
            f"mitsubishi:preset:{preset}",
            "mitsubishi",
            "MitsubishiCommand",
            dict(
                mode="cool",
                temperature=24,
                native_fan=2,
                preset=preset,
                swing_v=False,
                swing_h=False,
            ),
            fan=4,
            setup=f"obj.preset=CLIMATE_PRESET_{wire};",
        )
    for temp in (61, 75, 89):
        extra(
            f"whynter:fahrenheit:{temp}",
            "whynter",
            "WhynterCommand",
            dict(mode="cool", fan="high", temperature=temp, fahrenheit=True),
            fan=5,
            temperature=(temp - 32) * 5 / 9,
            setup="obj.fahrenheit_=true;",
        )
    for enabled, report in ((False, False), (True, False), (True, True)):
        extra(
            f"toshiba_rac:comfort-sense:{enabled}:{report}",
            "toshiba_1",
            "ToshibaRacCommand.comfort_sense",
            dict(mode="cool", temperature=23, enabled=enabled, send_temperature=report),
            setup="obj.sensor_=&obj;obj.current_temperature=23;",
            invoke=f"obj.transmit_rac_pt1411hwru_temp_({str(enabled).lower()},{str(report).lower()});",
        )
    extra(
        "toshiba_ras2819:swing-toggle",
        "toshiba_3",
        "ToshibaRas2819Command.swing_toggle",
        {},
        invoke="obj.transmit_state();transmissions.clear();obj.swing_mode=CLIMATE_SWING_VERTICAL;obj.transmit_state();",
    )
    for mode, fan, temp in product((1, 2, 3, 4, 5), (2, 3, 4, 5), (17, 24, 30)):
        if mode == 5 and fan != 2:
            continue
        extra(
            f"toshiba_ras25:{MODES[mode]}:{FANS[fan]}:{temp}",
            "toshiba_6",
            "ToshibaRas25j2kvsgNdCommand.climate",
            dict(mode=MODES[mode], fan=FANS[fan], temperature=temp),
            mode=mode,
            fan=fan,
            temperature=temp,
            invoke="obj.transmit_frame_(decltype(obj)::ToshibaPreset::TOSHIBA_PRESET_NONE);",
        )
    for wire_model, factory in (
        ("DG11J1_3A", "WhirlpoolCommand"),
        ("DG11J1_91", "WhirlpoolDg11j191Command"),
        ("HISENSE_ARG", "HisenseArgCommand"),
    ):
        for mode, was_on, swing in product(range(6), (False, True), (0, 2)):
            power_toggle = was_on != (mode != 0)
            args = dict(
                mode=MODES[mode] if mode else "cool",
                temperature=24,
                fan="auto",
                off_command=not mode,
                power_toggle=power_toggle,
            )
            args["swing_v" if wire_model == "HISENSE_ARG" else "swing_toggle"] = bool(
                swing
            )
            extra(
                f"whirlpool:{wire_model}:{mode}:{was_on}:{swing}",
                "whirlpool",
                factory,
                args,
                mode=mode,
                swing=swing,
                setup=f"obj.model_=whirlpool::MODEL_{wire_model};obj.powered_on_assumed={str(was_on).lower()};obj.send_swing_cmd_={str(bool(swing)).lower()};",
            )
    for preset, args in (
        ("BOOST", dict(boost=True, fan="high")),
        ("SLEEP", dict(fan="quiet")),
    ):
        extra(
            f"zhlt01:preset:{preset}",
            "zhlt01",
            "Zhlt01Command",
            dict(mode="cool", temperature=24, **args),
            setup=f"obj.preset=CLIMATE_PRESET_{preset};",
        )
    for model in (4, 6):
        extra(
            f"gree_{model}:sleep",
            f"gree_{model}",
            "GreeModelCommand",
            dict(model=GREE[model], mode="cool", temperature=24, sleep=True),
            setup="obj.preset=CLIMATE_PRESET_SLEEP;",
        )
    for model, temp in product(range(9), (60, 72, 86)):
        extra(
            f"gree_{model}:fahrenheit:{temp}",
            f"gree_{model}",
            "GreeModelCommand",
            dict(model=GREE[model], mode="cool", temperature=temp, fahrenheit=True),
            temperature=(temp - 32) * 5 / 9,
            setup="obj.use_fahrenheit_=true;",
        )
    for model, features in ((1, 0), (1, 0xF0), (5, 0xB0), (6, 0)):
        extra(
            f"gree_{model}:features:{features}",
            f"gree_{model}",
            "GreeModelCommand",
            dict(
                model=GREE[model],
                mode="cool",
                temperature=24,
                features=features,
                fan="high" if model == 5 else "auto",
            ),
            fan=5 if model == 5 else 2,
            setup=f"obj.feature_bits_={features};",
        )
    extra(
        "gree_6:quiet",
        "gree_6",
        "GreeModelCommand",
        dict(model="yx1ff", mode="cool", temperature=24, fan="quiet"),
        fan=9,
    )
    for fahrenheit, temp in ((False, 24), (True, 60), (True, 72), (True, 90)):
        extra(
            f"daikin_brc:units:{fahrenheit}:{temp}",
            "daikin_brc",
            "DaikinBrcFahrenheitCommand" if fahrenheit else "DaikinBrcCommand",
            dict(
                mode="cool",
                temperature=temp,
                fan="low",
                swing=False,
                sub_unit=3,
                mode_button=True,
            ),
            fan=3,
            temperature=(temp - 32) * 5 / 9 if fahrenheit else temp,
            setup=f"obj.fahrenheit_={str(fahrenheit).lower()};obj.sub_unit_=3;obj.mode_button_=4;",
        )
    for temp in (61, 72, 88):
        extra(
            f"mitsubishi:fahrenheit:{temp}",
            "mitsubishi",
            "MitsubishiCommand",
            dict(mode="cool", temperature=temp, native_fan=0, fahrenheit=True),
            temperature=(temp - 32) * 5 / 9,
            setup="obj.fahrenheit_compatibility_=true;",
        )
    for vertical, horizontal in ((1, 1), (3, 5), (5, 8)):
        extra(
            f"mitsubishi:vanes:{vertical}:{horizontal}",
            "mitsubishi",
            "MitsubishiCommand",
            dict(
                mode="cool",
                temperature=24,
                native_fan=0,
                vertical_position=vertical,
                horizontal_position=horizontal,
                dual_vanes=True,
            ),
            setup=f"obj.default_vertical_direction_=static_cast<mitsubishi::VerticalDirection>({vertical << 3});obj.default_horizontal_direction_=static_cast<mitsubishi::HorizontalDirection>({horizontal << 4});obj.vertical_vanes_=2;",
        )
    for direction, display, sleep in ((1, True, False), (4, False, True)):
        extra(
            f"airton:settings:{direction}:{display}:{sleep}",
            "airton",
            "AirtonCommand",
            dict(
                mode="cool",
                temperature=24,
                direction=direction,
                display=display,
                sleep=sleep,
            ),
            setup=f"obj.settings_.vertical_direction=static_cast<airton::VerticalDirection>({direction});obj.settings_.display_state={str(display).lower()};obj.settings_.sleep_state={str(sleep).lower()};",
        )
    extra(
        "hitachi_ac344:off-after-cool",
        "hitachi_ac344",
        "HitachiAc344Command",
        dict(
            mode="cool",
            temperature=24,
            power=False,
            fan="auto",
            swing_v=False,
            horizontal_position=3,
        ),
        invoke="obj.transmit_state();transmissions.clear();obj.mode=CLIMATE_MODE_OFF;obj.transmit_state();",
    )
    for component in ("toshiba_1", "toshiba_2"):
        extra(
            f"{component}:swing-on",
            component,
            "ToshibaRacCommand.climate",
            dict(
                mode="cool",
                temperature=75 if component.endswith("2") else 24,
                fahrenheit=component.endswith("2"),
            ),
            temperature=(75 - 32) * 5 / 9 if component.endswith("2") else 24,
            swing=2,
        )
    extra(
        "toshiba_ras25:off",
        "toshiba_6",
        "ToshibaRas25j2kvsgNdCommand.climate",
        dict(mode="cool", temperature=24, power=False),
        mode=0,
        invoke="obj.transmit_frame_(decltype(obj)::ToshibaPreset::TOSHIBA_PRESET_NONE);",
    )
    for preset in (
        "boost",
        "eco",
        "fireplace_1",
        "fireplace_2",
        "frost_protection",
        "hada_care",
        "sleep_1h",
        "sleep_3h",
        "sleep_5h",
        "sleep_9h",
    ):
        temp = 8 if preset == "frost_protection" else 24
        extra(
            f"toshiba_ras25:preset:{preset}",
            "toshiba_6",
            "ToshibaRas25j2kvsgNdCommand.climate",
            dict(mode="heat", temperature=temp, preset=preset),
            mode=3,
            temperature=temp,
            invoke=f"obj.transmit_frame_(decltype(obj)::ToshibaPreset::TOSHIBA_PRESET_{preset.upper()});",
        )
    for power in range(5):
        extra(
            f"toshiba_ras25:power:{power}",
            "toshiba_6",
            "ToshibaRas25j2kvsgNdCommand.climate",
            dict(mode="cool", temperature=24, power_selection=power),
            setup=f"obj.power_selection_=static_cast<decltype(obj)::ToshibaPowerSelection>({power});",
            invoke="obj.transmit_frame_(decltype(obj)::ToshibaPreset::TOSHIBA_PRESET_NONE);",
        )
    for action in (0, 4):
        extra(
            f"toshiba_ras25:motion:{action}",
            "toshiba_6",
            "ToshibaRas25j2kvsgNdCommand.motion",
            dict(action=action),
            invoke=f"obj.transmit_motion_({action},{0 if action == 0 else 1});",
        )
    for humidity, target in ((0, 39), (45, 45), (50, 50), (255, 53)):
        extra(
            f"daikin_arc:humidity:{humidity}",
            "daikin_arc",
            "DaikinArcCommand",
            dict(mode="cool", temperature=24, humidity=humidity, humidity_changed=True),
            setup=f"obj.target_humidity={target};",
        )
    extra(
        "pd_pioneer_ir:eco",
        "pd_pioneer_ir",
        "PdPioneerClimateCommand",
        dict(mode="cool", temperature=24, economy=True),
        setup="obj.preset=CLIMATE_PRESET_ECO;",
    )
    return result


def expected_state(factory, args):
    """Specify observable fields from requested settings and remote limitations."""
    state = dict(
        power=None, mode=None, temperature=None, fan=None, swing_v=None, swing_h=None
    )
    if factory.endswith("power_off") or factory == "FriedrichUtilityCommand":
        state["power"] = False
        return state
    if factory.endswith(".swing"):
        state["swing_v"] = args["enabled"]
        return state
    if factory.endswith((".swing_toggle", ".comfort_sense", ".motion")):
        return state
    power = args.get("power", True)
    mode = args.get("mode", "cool")
    temp = args.get("temperature", 24)
    state.update(
        power=power,
        mode=mode if power else None,
        temperature=temp,
        fan=args.get("fan", "auto"),
    )
    for axis in ("swing_v", "swing_h"):
        if axis in args:
            state[axis] = args[axis]
    if factory in (
        "AirtonCommand",
        "MitsubishiCommand",
        "HitachiAc344Command",
        "HitachiAc424Command",
        "RemkoAr715Command",
    ):
        state["mode"] = mode
    if factory == "AirtonCommand":
        state.update(
            temperature=None if power and mode == "auto" else temp,
            swing_v=args.get("direction", 0) == 1,
        )
    if factory == "DaikinArcCommand" and power and mode in ("auto", "dry", "fan_only"):
        state["temperature"] = None
    if factory == "DaikinArcCommand":
        state.update(
            swing_v=args.get("swing_v", False),
            swing_h=args.get("swing_h", False),
            fan={"auto": 10, "quiet": 11, "low": 3, "medium": 5, "high": 7}[
                args.get("fan", "auto")
            ],
        )
    if factory in ("DaikinBrcCommand", "DaikinBrcFahrenheitCommand"):
        state.update(swing_v=args["swing"], swing_h=args["swing"])
        if power and mode in ("dry", "fan_only"):
            state["temperature"] = None
        elif factory == "DaikinBrcFahrenheitCommand":
            state["temperature"] = (temp - 32) * 5 / 9
    if factory == "DelonghiCommand" and not power:
        state["temperature"] = None
    if factory == "HaierTundraCommand" and not power:
        state["swing_v"] = None
    if factory in ("FriedrichCommand", "IslandaireCommand") or args.get("fahrenheit"):
        state["temperature"] = (temp - 32) * 5 / 9
    if factory == "MitsubishiCommand":
        state["fan"] = args["native_fan"]
        state.update(
            swing_v=args.get("swing_v", False), swing_h=args.get("swing_h", False)
        )
        if mode == "dry":
            state["temperature"] = None
        if args.get("preset") == "night":
            state.update(fan=0, swing_v=False)
        if args.get("fahrenheit"):
            state["temperature"] = {61: 16, 72: 22.5, 88: 31}[temp]
    if factory.startswith("Hitachi"):
        state["swing_h"] = args["horizontal_position"] == 0
    if factory in ("WhirlpoolCommand", "WhirlpoolDg11j191Command", "HisenseArgCommand"):
        state.update(power=None, mode=None if args["off_command"] else mode)
        if factory == "HisenseArgCommand":
            if args["off_command"] and not args["power_toggle"]:
                state["mode"] = "cool"
            state["swing_v"] = args["swing_v"]
            if mode == "cool" and args["power_toggle"]:
                state["mode"] = None
            if mode == "fan_only":
                state["temperature"] = None
                state["fan"] = "medium"
    if factory == "EmmetiCommand":
        if not power:
            return dict(
                power=False,
                mode=None,
                temperature=None,
                fan=None,
                swing_v=None,
                swing_h=None,
            )
        state["swing_v"] = args["blade"] == 1
    if factory == "GreeModelCommand":
        state["swing_v"] = args.get("swing_v", False)
        state["swing_h"] = args.get("swing_h", False)
        if args["model"] == "yb1fa" and args.get("features", 0) & 16:
            state["fan"] = "high"
        if args["model"] not in ("yac", "yag", "yaw1f"):
            state["swing_h"] = None
        if args["model"] == "generic":
            state["swing_v"] = False
    if factory == "Zhlt01Command":
        state.update(
            swing_v=args.get("swing_v", False), swing_h=args.get("swing_h", False)
        )
    if factory == "RemkoAr715Command" and mode in ("dry", "fan_only"):
        state["fan"] = None
    if factory == "PdPioneerClimateCommand":
        state.update(
            swing_v=args.get("swing_v", False), swing_h=args.get("swing_h", False)
        )
        if not power or mode == "fan_only":
            state["temperature"] = None
    if factory in (
        "ToshibaCommand.climate",
        "ToshibaRasB10n3kv2Command.climate",
        "ToshibaSeiyaCommand.climate",
        "ToshibaRas25j2kvsgNdCommand.climate",
    ):
        state["fan"] = {"auto": 0, "quiet": 1, "low": 2, "medium": 4, "high": 6}[
            args.get("fan", "auto")
        ]
    if factory == "ToshibaSeiyaCommand.climate" and not power:
        state["fan"] = None
    if factory == "ToshibaRas25j2kvsgNdCommand.climate" and mode == "fan_only":
        state["temperature"] = None
    if (
        factory in ("ToshibaRacCommand.climate", "ToshibaRas2819Command.climate")
        and mode == "fan_only"
    ):
        state["temperature"] = None
    if factory == "ToshibaRas2819Command.climate" and mode == "dry" and temp != 25:
        state["temperature"] = None
    return state
