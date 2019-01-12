import argparse
import colour
import importlib.util
import os
import sys
import types

import manimlib.constants


def parse_cli():
    try:
        parser = argparse.ArgumentParser()
        module_location = parser.add_mutually_exclusive_group()
        module_location.add_argument(
            "file",
            nargs="?",
            help="path to file holding the python code for the scene",
        )
        parser.add_argument(
            "scene_names",
            nargs="+",
            help="Name of the Scene class you want to see",
        )
        optional_args = [
            ("-p", "--preview"),
            ("-w", "--write_to_movie"),
            ("-s", "--show_last_frame"),
            ("-l", "--low_quality"),
            ("-m", "--medium_quality"),
            ("-g", "--save_pngs"),
            ("-f", "--show_file_in_finder"),
            ("-t", "--transparent"),
            ("-q", "--quiet"),
            ("-a", "--write_all")
        ]
        for short_arg, long_arg in optional_args:
            parser.add_argument(short_arg, long_arg, action="store_true")
        parser.add_argument("-o", "--output_file_name")
        parser.add_argument("-n", "--start_at_animation_number")
        parser.add_argument("-r", "--resolution")
        parser.add_argument("-c", "--color")
        parser.add_argument(
            "--sound",
            action="store_true",
            help="Play a success/failure sound",
        )
        module_location.add_argument(
            "--livestream",
            action="store_true",
            help="Run in streaming mode",
        )
        parser.add_argument(
            "--to-twitch",
            action="store_true",
            help="Stream to twitch",
        )
        parser.add_argument(
            "--with-key",
            dest="twitch_key",
            help="Stream key for twitch",
        )
        args = parser.parse_args()

        if args.file is None and not args.livestream:
            parser.print_help()
            sys.exit(2)
        if args.to_twitch and not args.livestream:
            print("You must run in streaming mode in order to stream to twitch")
            sys.exit(2)
        if args.to_twitch and args.twitch_key is None:
            print("Specify the twitch stream key with --with-key")
            sys.exit(2)
        return args
    except argparse.ArgumentError as err:
        print(str(err))
        sys.exit(2)


def get_module(file_name):
    if file_name == "-":
        module = types.ModuleType("input_scenes")
        code = "from big_ol_pile_of_manim_imports import *\n\n" + sys.stdin.read()
        try:
            exec(code, module.__dict__)
            return module
        except Exception as e:
            print(f"Failed to render scene: {str(e)}")
            sys.exit(2)
    else:
        module_name = file_name.replace(os.sep, ".").replace(".py", "")
        spec = importlib.util.spec_from_file_location(module_name, file_name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def get_configuration(args):
    if args.output_file_name is not None:
        output_file_name_root, output_file_name_ext = os.path.splitext(
            args.output_file_name)
        expected_ext = '.png' if args.show_last_frame else '.mp4'
        if output_file_name_ext not in ['', expected_ext]:
            print("WARNING: The output will be to (doubly-dotted) %s%s" %
                  output_file_name_root % expected_ext)
            output_file_name = args.output_file_name
        else:
            # If anyone wants .mp4.mp4 and is surprised to only get .mp4, or such... Well, too bad.
            output_file_name = output_file_name_root
    else:
        output_file_name = args.output_file_name

    config = {
        "module": get_module(args.file),
        "scene_names": args.scene_names,
        "open_video_upon_completion": args.preview,
        "show_file_in_finder": args.show_file_in_finder,
        # By default, write to file
        "write_to_movie": args.write_to_movie or not args.show_last_frame,
        "show_last_frame": args.show_last_frame,
        "save_pngs": args.save_pngs,
        # If -t is passed in (for transparent), this will be RGBA
        "saved_image_mode": "RGBA" if args.transparent else "RGB",
        "movie_file_extension": ".mov" if args.transparent else ".mp4",
        "quiet": args.quiet or args.write_all,
        "ignore_waits": args.preview,
        "write_all": args.write_all,
        "output_file_name": output_file_name,
        "start_at_animation_number": args.start_at_animation_number,
        "end_at_animation_number": None,
        "sound": args.sound,
    }

    # Camera configuration
    config["camera_config"] = {}
    if args.low_quality:
        config["camera_config"].update(manimlib.constants.LOW_QUALITY_CAMERA_CONFIG)
        config["frame_duration"] = manimlib.constants.LOW_QUALITY_FRAME_DURATION
    elif args.medium_quality:
        config["camera_config"].update(manimlib.constants.MEDIUM_QUALITY_CAMERA_CONFIG)
        config["frame_duration"] = manimlib.constants.MEDIUM_QUALITY_FRAME_DURATION
    else:
        config["camera_config"].update(manimlib.constants.PRODUCTION_QUALITY_CAMERA_CONFIG)
        config["frame_duration"] = manimlib.constants.PRODUCTION_QUALITY_FRAME_DURATION

    # If the resolution was passed in via -r
    if args.resolution:
        if "," in args.resolution:
            height_str, width_str = args.resolution.split(",")
            height = int(height_str)
            width = int(width_str)
        else:
            height = int(args.resolution)
            width = int(16 * height / 9)
        config["camera_config"].update({
            "pixel_height": height,
            "pixel_width": width,
        })

    if args.color:
        try:
            config["camera_config"]["background_color"] = colour.Color(args.color)
        except AttributeError as err:
            print("Please use a valid color")
            print(err)
            sys.exit(2)

    # If rendering a transparent image/move, make sure the
    # scene has a background opacity of 0
    if args.transparent:
        config["camera_config"]["background_opacity"] = 0

    # Arguments related to skipping
    stan = config["start_at_animation_number"]
    if stan is not None:
        if "," in stan:
            start, end = stan.split(",")
            config["start_at_animation_number"] = int(start)
            config["end_at_animation_number"] = int(end)
        else:
            config["start_at_animation_number"] = int(stan)

    config["skip_animations"] = any([
        config["show_last_frame"] and not config["write_to_movie"],
        config["start_at_animation_number"],
    ])
    return config