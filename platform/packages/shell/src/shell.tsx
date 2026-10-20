import type { PropsWithChildren, ReactNode } from "react";
import { useSharedNavigation } from "./use-shared-navigation";
import {
  type ProjectId,
} from "@quant-research/project-registry";
import {
  Disclosure,
  SupportingCopy,
  ThemeToggle,
  classNames,
  type RetainedVisibleCopy,
} from "@quant-research/ui";

export interface SharedNavigationProps {
  currentProject: ProjectId;
}

export function SharedNavigation({ currentProject }: SharedNavigationProps) {
  const { brand, navigation } = useSharedNavigation(currentProject);
  return (
    <header className="qr-nav-shell quant-shared-nav" data-quant-navigation-managed="react">
      <a className="qr-skip-link" href="#main-content">
        본문으로 건너뛰기
      </a>
      <div className="qr-nav-shell__inner quant-shared-nav__inner">
          <a
            className="qr-nav-shell__brand quant-shared-nav__brand"
            href={brand.url}
            aria-current={brand.current ? "page" : undefined}
          >
            {brand.label}
          </a>
        <nav aria-label="프로젝트" className="qr-project-nav quant-shared-nav__links">
          {navigation.map((project) => (
            <a
              aria-current={project.current ? "page" : undefined}
              className={classNames(
                "qr-project-nav__link quant-shared-nav__link",
                project.current && "qr-project-nav__link--current is-active",
              )}
              href={project.url}
              key={project.id}
            >
              {project.label}
            </a>
          ))}
        </nav>
        <span className="quant-shared-nav__theme"><ThemeToggle /></span>
      </div>
    </header>
  );
}

export interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  supportingCopy?: RetainedVisibleCopy;
  action?: ReactNode;
}

export function PageHeader({
  eyebrow,
  title,
  supportingCopy,
  action,
}: PageHeaderProps) {
  return (
    <div className="qr-page-header">
      <div className="qr-page-header__copy">
        {eyebrow ? <span className="qr-page-header__eyebrow">{eyebrow}</span> : null}
        <h1>{title}</h1>
        {supportingCopy ? (
          <SupportingCopy copy={supportingCopy} role="hero-support" />
        ) : null}
      </div>
      {action ? <div className="qr-page-header__action">{action}</div> : null}
    </div>
  );
}

export interface DashboardShellProps extends PropsWithChildren {
  currentProject: ProjectId;
  eyebrow?: string;
  title: string;
  supportingCopy?: RetainedVisibleCopy;
  headerAction?: ReactNode;
  operationsDetails?: ReactNode;
}

export function DashboardShell({
  currentProject,
  eyebrow,
  title,
  supportingCopy,
  headerAction,
  operationsDetails,
  children,
}: DashboardShellProps) {
  return (
    <>
      <SharedNavigation currentProject={currentProject} />
      <main className="qr-dashboard" id="main-content" tabIndex={-1}>
        <PageHeader
          action={headerAction}
          eyebrow={eyebrow}
          supportingCopy={supportingCopy}
          title={title}
        />
        {children}
        {operationsDetails ? (
          <Disclosure
            className="qr-operations-details"
            summary="데이터 · 출처 · 운영 상세"
          >
            {operationsDetails}
          </Disclosure>
        ) : null}
      </main>
    </>
  );
}
