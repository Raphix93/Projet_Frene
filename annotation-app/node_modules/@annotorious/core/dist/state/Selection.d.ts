import { Annotation, FormatAdapter } from '../model';
import { Store } from './Store';
export interface Selection {
    selected: {
        id: string;
        editable?: boolean;
    }[];
    event?: PointerEvent | KeyboardEvent;
}
export type SelectionState<I extends Annotation, E extends unknown> = ReturnType<typeof createSelectionState<I, E>>;
export declare enum UserSelectAction {
    EDIT = "EDIT",// Make annotation target(s) editable on pointer select
    SELECT = "SELECT",// Just select, but don't make editable
    NONE = "NONE"
}
export type UserSelectActionExpression<T extends unknown> = UserSelectAction | ((a: T) => UserSelectAction);
export declare const createSelectionState: <I extends Annotation, E extends unknown>(store: Store<I>, defaultSelectionAction?: UserSelectActionExpression<E>, adapter?: FormatAdapter<I, E>) => {
    readonly event: PointerEvent | KeyboardEvent;
    readonly selected: {
        id: string;
        editable?: boolean;
    }[];
    readonly userSelectAction: UserSelectActionExpression<E>;
    clear: () => void;
    evalSelectAction: (annotation: I) => UserSelectAction;
    isEmpty: () => boolean;
    isSelected: (annotationOrId: I | string) => boolean;
    setSelected: (idOrIds: string | string[], editable?: boolean) => void;
    setUserSelectAction: (action: UserSelectActionExpression<E> | undefined) => void;
    subscribe: any;
    userSelect: (idOrIds: string | string[], event?: Selection["event"]) => void;
};
export declare const onUserSelect: <I extends Annotation, E extends unknown>(annotation: I, action?: UserSelectActionExpression<E>, adapter?: FormatAdapter<I, E>) => UserSelectAction;
//# sourceMappingURL=Selection.d.ts.map