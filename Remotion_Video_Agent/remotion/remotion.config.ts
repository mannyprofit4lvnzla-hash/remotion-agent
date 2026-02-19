import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setDelayRenderTimeoutInSeconds(120); // Increase timeout to 2 minutes
Config.setConcurrency(1); // To save memory on small instances
