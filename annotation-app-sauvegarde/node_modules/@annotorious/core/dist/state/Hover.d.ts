import { Annotation } from '../model';
import { Store } from './Store';
export type HoverState<T extends Annotation> = ReturnType<typeof createHoverState<T>>;
export declare const createHoverState: <T extends Annotation>(store: Store<T>) => {
    readonly current: string;
    subscribe: any;
    set: any;
};
//# sourceMappingURL=Hover.d.ts.map