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
    if component == "gree_6":
        args["swing_h"] = vertical
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
                swing=0,
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
    if factory.endswith((".swing_toggle", ".comfort_sense")):
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
            temperature=25 if power and mode == "auto" else temp, swing_v=False
        )
    if factory == "DaikinArcCommand" and power and mode in ("auto", "dry", "fan_only"):
        state["temperature"] = None
    if factory == "DaikinArcCommand":
        state.update(
            swing_v=args.get("swing_v", False), swing_h=args.get("swing_h", False)
        )
    if factory == "DaikinBrcCommand":
        state.update(swing_v=args["swing"], swing_h=args["swing"])
        if power and mode in ("dry", "fan_only"):
            state["temperature"] = None
    if factory == "DelonghiCommand" and not power:
        state["temperature"] = None
    if factory == "HaierTundraCommand" and not power:
        state["swing_v"] = None
    if factory in ("FriedrichCommand", "IslandaireCommand") or args.get("fahrenheit"):
        state["temperature"] = (temp - 32) * 5 / 9
    if factory == "MitsubishiCommand":
        state["fan"] = {0: "auto", 1: "low"}.get(args["native_fan"], args["native_fan"])
        if mode == "dry":
            state["temperature"] = 24
        if args.get("preset") == "night":
            state.update(fan="auto", swing_v=False)
    if factory.startswith("Hitachi"):
        state["swing_h"] = args["horizontal_position"] == 0
    if factory == "WhirlpoolCommand":
        state.update(power=None, mode=None if args["off_command"] else mode)
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
        if args["model"] not in ("yac", "yag", "yaw1f"):
            state["swing_h"] = None
        if args["model"] == "generic":
            state["swing_v"] = False
    if factory == "RemkoAr715Command" and mode in ("dry", "fan_only"):
        state["fan"] = None
    if factory == "PdPioneerClimateCommand" and (not power or mode == "fan_only"):
        state["temperature"] = None
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
