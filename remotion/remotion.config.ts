import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setJpegQuality(90);
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');
