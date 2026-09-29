/// <reference types="vite/client" />

declare namespace JSX {
  interface Element {
    type: unknown;
    props: unknown;
    key: unknown;
  }
  interface IntrinsicElements {
    [elemName: string]: Record<string, unknown>;
  }
}

declare module 'react' {
  export type ReactNode =
    | string
    | number
    | boolean
    | null
    | undefined
    | JSX.Element
    | Iterable<ReactNode>;

  export interface FC<P = Record<string, unknown>> {
    (props: P): JSX.Element | null;
  }

  export function useState<T>(
    initialState: T | (() => T)
  ): [T, (newState: T | ((prev: T) => T)) => void];

  export function useEffect(
    effect: () => void | (() => void),
    deps?: readonly unknown[]
  ): void;
}

declare module 'react-dom/client' {
  export interface Root {
    render(children: unknown): void;
    unmount(): void;
  }
  export function createRoot(container: Element | DocumentFragment): Root;
}

declare module 'react-router-dom' {
  import type { FC, ReactNode } from 'react';

  export interface BrowserRouterProps {
    children?: ReactNode;
  }
  export const BrowserRouter: FC<BrowserRouterProps>;

  export interface RoutesProps {
    children?: ReactNode;
  }
  export const Routes: FC<RoutesProps>;

  export interface RouteProps {
    path?: string;
    index?: boolean;
    element?: ReactNode;
  }
  export const Route: FC<RouteProps>;

  export interface LinkProps {
    to: string;
    className?: string;
    children?: ReactNode;
  }
  export const Link: FC<LinkProps>;

  export interface NavLinkProps {
    to: string;
    end?: boolean;
    className?: string | ((props: { isActive: boolean }) => string);
    style?:
      | Record<string, string | number>
      | ((props: { isActive: boolean }) => Record<string, string | number>);
    children?: ReactNode;
  }
  export const NavLink: FC<NavLinkProps>;
}

declare module 'react/jsx-runtime' {
  export namespace JSX {
    interface Element {
      type: unknown;
      props: unknown;
      key: unknown;
    }
    interface IntrinsicElements {
      [elemName: string]: Record<string, unknown>;
    }
  }
  export function jsx(
    type: unknown,
    props: unknown,
    key?: unknown
  ): JSX.Element;
  export function jsxs(
    type: unknown,
    props: unknown,
    key?: unknown
  ): JSX.Element;
  export const Fragment: unknown;
}

declare module 'react/jsx-dev-runtime' {
  export namespace JSX {
    interface Element {
      type: unknown;
      props: unknown;
      key: unknown;
    }
    interface IntrinsicElements {
      [elemName: string]: Record<string, unknown>;
    }
  }
  export function jsxDEV(
    type: unknown,
    props: unknown,
    key: unknown,
    isStatic: boolean,
    source?: unknown,
    self?: unknown
  ): JSX.Element;
  export const Fragment: unknown;
}

declare module '@fontsource/ibm-plex-sans';
declare module '@fontsource/ibm-plex-mono';
