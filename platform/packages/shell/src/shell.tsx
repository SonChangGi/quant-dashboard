import type { PropsWithChildren, ReactNode } from "react";
import {
  getCanonicalNavigation,
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
  const navigation = getCanonicalNavigation(currentProject);
  return (
    <header className="qr-nav-shell">
      <a className="qr-skip-link" href="#main-content">
        본문으로 건너뛰기
      </a>
      <div className="qr-nav-shell__inner">
        <div className="qr-nav-shell__primary">
          <a
            className="qr-nav-shell__brand"
            href="https://sonchanggi.github.io/quant-dashboard/"
          >
            Quant Research Hub
          </a>
          <ThemeToggle />
        </div>
        <nav aria-label="프로젝트" className="qr-project-nav">
          {navigation.map((project) => (
            <a
              aria-current={project.current ? "page" : undefined}
              className={classNames(
                "qr-project-nav__link",
                project.current && "qr-project-nav__link--current",
              )}
              href={project.url}
              key={project.id}
            >
              {project.label}
            </a>
          ))}
        </nav>
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
