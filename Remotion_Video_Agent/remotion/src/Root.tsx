import { Composition } from 'remotion';
import { MyComposition, myCompSchema } from './Composition';

export const RemotionRoot: React.FC = () => {
    return (
        <>
            <Composition
                id="MyComposition"
                component={MyComposition}
                durationInFrames={300} // 10 seconds at 30fps
                fps={30}
                width={1080}
                height={1920}
                schema={myCompSchema}
                defaultProps={{
                    videoUrl: '', // Will be overridden
                    videoStart: 0,
                    musicUrl: '',
                    musicStart: 0,
                    quoteText: 'Inspiring Quote Here',
                }}
            />
        </>
    );
};
