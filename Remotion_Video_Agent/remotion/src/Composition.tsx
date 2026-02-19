import { AbsoluteFill, Audio, Video, useVideoConfig, interpolate, useCurrentFrame } from 'remotion';
import { z } from 'zod';

export const myCompSchema = z.object({
    videoUrl: z.string(),
    videoStart: z.number(),
    musicUrl: z.string(),
    musicStart: z.number(),
    quoteText: z.string(),
});

export const MyComposition: React.FC<z.infer<typeof myCompSchema>> = ({
    videoUrl,
    videoStart,
    musicUrl,
    musicStart,
    quoteText,
}) => {
    const frame = useCurrentFrame();
    const { fps, durationInFrames } = useVideoConfig();

    // Fade in animation for text
    const opacity = interpolate(frame, [0, 30], [0, 1], {
        extrapolateRight: 'clamp',
    });

    return (
        <AbsoluteFill style={{ backgroundColor: 'black' }}>
            {/* 1. Background Video */}
            {videoUrl && (
                <Video
                    src={videoUrl}
                    startFrom={Math.round(videoStart * fps)} // Convert seconds to frames
                    endAt={Math.round((videoStart * fps) + durationInFrames)} // Ensure 10s duration
                    style={{
                        objectFit: 'cover',
                        width: '100%',
                        height: '100%',
                    }}
                    // Mute original video audio if we are replacing it
                    volume={0}
                />
            )}

            {/* 2. Cinematic Dark Overlay */}
            <AbsoluteFill
                style={{
                    backgroundColor: 'black',
                    opacity: 0.4, // Adjust for darkness
                }}
            />

            {/* 3. Inspirational Text */}
            <AbsoluteFill
                style={{
                    justifyContent: 'center',
                    alignItems: 'center',
                    padding: 80,
                    textAlign: 'center',
                }}
            >
                <div
                    style={{
                        fontFamily: 'sans-serif', // We can add Google Fonts later
                        fontSize: 70,
                        color: 'white',
                        fontWeight: 'bold',
                        lineHeight: 1.3,
                        textShadow: '0px 2px 10px rgba(0,0,0,0.8)',
                        opacity,
                        whiteSpace: 'pre-line', // Allow newlines in quote
                    }}
                >
                    {quoteText}
                </div>
            </AbsoluteFill>

            {/* 4. Background Music */}
            {musicUrl && (
                <Audio
                    src={musicUrl}
                    startFrom={Math.round(musicStart * fps)}
                    volume={0.8}
                />
            )}
        </AbsoluteFill>
    );
};
