import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setDelayRenderTimeoutInSeconds(120);
Config.setConcurrency(1); // To save memory on small instances
