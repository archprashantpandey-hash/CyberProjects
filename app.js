let currentProjects = [...projects];

let currentStatus = "all";

let currentView = "dashboard";

const projectGrid =
    document.getElementById("projectGrid");

const allProjectGrid =
    document.getElementById("allProjectGrid");

const favoriteGrid =
    document.getElementById("favoriteGrid");

const searchInput =
    document.getElementById("searchInput");

const projectModal =
    document.getElementById("projectModal");

const addModal =
    document.getElementById("addModal");

const modalContent =
    document.getElementById("modalContent");


/* =========================================================
   INITIALIZATION
========================================================= */

function init() {

    updateStats();

    renderDashboard();

    renderAllProjects();

    renderFavorites();

    setupNavigation();

    setupSearch();

    setupFilters();

    setupModals();

    setupKeyboardShortcuts();

}

init();


/* =========================================================
   STATISTICS
========================================================= */

function updateStats() {

    document.getElementById("totalProjects")
        .textContent = projects.length;

    document.getElementById("developmentProjects")
        .textContent =
        projects.filter(
            p => p.status === "Building"
        ).length;

    document.getElementById("researchProjects")
        .textContent =
        projects.filter(
            p => p.status === "Researching"
        ).length;

    document.getElementById("favoriteProjects")
        .textContent =
        projects.filter(
            p => p.favorite
        ).length;

}


/* =========================================================
   PROJECT CARD
========================================================= */

function createProjectCard(project) {

    const card = document.createElement("article");

    card.className = "project-card";

    card.innerHTML = `

        <div class="project-card-top">

            <div class="project-icon">
                ${project.icon}
            </div>

            <button
                class="favorite-button ${project.favorite ? "is-favorite" : ""}"
                data-id="${project.id}"
                title="Favorite"
            >
                ${project.favorite ? "★" : "☆"}
            </button>

        </div>


        <div class="project-meta">

            <span class="category">
                ${project.category}
            </span>

            <span class="status status-${project.status.toLowerCase()}">
                ${project.status}
            </span>

        </div>


        <h3>
            ${project.title}
        </h3>


        <p>
            ${project.description}
        </p>


        <div class="technology-list">

            ${project.technologies
                .slice(0, 4)
                .map(
                    tech =>
                    `<span>${tech}</span>`
                )
                .join("")
            }

        </div>


        <button
            class="open-project"
            data-id="${project.id}"
        >
            Open project
            <span>→</span>
        </button>

    `;


    card.querySelector(
        ".open-project"
    ).addEventListener(
        "click",
        () => openProject(project.id)
    );


    card.querySelector(
        ".favorite-button"
    ).addEventListener(
        "click",
        event => {

            event.stopPropagation();

            toggleFavorite(project.id);

        }
    );


    return card;

}


/* =========================================================
   DASHBOARD
========================================================= */

function renderDashboard() {

    projectGrid.innerHTML = "";

    projects
        .slice(0, 6)
        .forEach(project => {

            projectGrid.appendChild(
                createProjectCard(project)
            );

        });

}


/* =========================================================
   ALL PROJECTS
========================================================= */

function renderAllProjects() {

    allProjectGrid.innerHTML = "";

    let filtered =
        projects.filter(project => {

            if (
                currentStatus === "all"
            ) {
                return true;
            }

            return (
                project.status ===
                currentStatus
            );

        });


    filtered.forEach(project => {

        allProjectGrid.appendChild(
            createProjectCard(project)
        );

    });


    if (!filtered.length) {

        allProjectGrid.innerHTML = `

            <div class="empty-state">

                <div>◌</div>

                <h3>
                    Nothing here yet
                </h3>

                <p>
                    No projects match this filter.
                </p>

            </div>

        `;

    }

}


/* =========================================================
   FAVORITES
========================================================= */

function renderFavorites() {

    favoriteGrid.innerHTML = "";

    const favorites =
        projects.filter(
            project => project.favorite
        );


    favorites.forEach(project => {

        favoriteGrid.appendChild(
            createProjectCard(project)
        );

    });


    if (!favorites.length) {

        favoriteGrid.innerHTML = `

            <div class="empty-state">

                <div>☆</div>

                <h3>
                    No favorites
                </h3>

                <p>
                    Star projects you want to keep close.
                </p>

            </div>

        `;

    }

}


/* =========================================================
   FAVORITE TOGGLE
========================================================= */

function toggleFavorite(id) {

    const project =
        projects.find(
            p => p.id === id
        );

    if (!project) return;

    project.favorite =
        !project.favorite;


    updateStats();

    renderDashboard();

    renderAllProjects();

    renderFavorites();

}


/* =========================================================
   OPEN PROJECT
========================================================= */

function openProject(id) {

    const project =
        projects.find(
            p => p.id === id
        );

    if (!project) return;


    const details =
        project.details;


    modalContent.innerHTML = `

        <div class="modal-project-header">

            <div class="project-icon large">
                ${project.icon}
            </div>

            <div>

                <span class="section-kicker">
                    ${project.category}
                </span>

                <h2>
                    ${project.title}
                </h2>

                <span class="status status-${project.status.toLowerCase()}">
                    ${project.status}
                </span>

            </div>

        </div>


        <p class="modal-description">
            ${project.description}
        </p>


        <div class="detail-section">

            <h3>
                Problem
            </h3>

            <p>
                ${details.problem}
            </p>

        </div>


        <div class="detail-section">

            <h3>
                Proposed solution
            </h3>

            <p>
                ${details.solution}
            </p>

        </div>


        <div class="detail-section">

            <h3>
                Architecture
            </h3>

            <div class="architecture-list">

                ${details.architecture
                    .map(
                        item =>
                        `<div>${item}</div>`
                    )
                    .join("")
                }

            </div>

        </div>


        <div class="detail-section">

            <h3>
                Core features
            </h3>

            <ul>

                ${details.features
                    .map(
                        item =>
                        `<li>${item}</li>`
                    )
                    .join("")
                }

            </ul>

        </div>


        <div class="detail-section">

            <h3>
                Technologies
            </h3>

            <div class="technology-list large-tags">

                ${project.technologies
                    .map(
                        tech =>
                        `<span>${tech}</span>`
                    )
                    .join("")
                }

            </div>

        </div>


        <div class="detail-section">

            <h3>
                Example
            </h3>

            <pre><code>${details.example}</code></pre>

        </div>


        <div class="detail-section">

            <h3>
                Open questions
            </h3>

            <ul>

                ${details.questions
                    .map(
                        question =>
                        `<li>${question}</li>`
                    )
                    .join("")
                }

            </ul>

        </div>

    `;


    projectModal.classList.add("visible");

}


/* =========================================================
   NAVIGATION
========================================================= */

function setupNavigation() {

    const navItems =
        document.querySelectorAll(
            ".nav-item"
        );


    navItems.forEach(item => {

        item.addEventListener(
            "click",
            () => {

                const view =
                    item.dataset.view;

                switchView(view);

            }
        );

    });


    document
        .getElementById("viewAllButton")
        .addEventListener(
            "click",
            () => switchView("projects")
        );

}


function switchView(view) {

    currentView = view;


    document
        .querySelectorAll(".view")
        .forEach(section => {

            section.classList.remove(
                "active-view"
            );

        });


    const target =
        document.getElementById(
            `${view}View`
        );


    if (target) {

        target.classList.add(
            "active-view"
        );

    }


    document
        .querySelectorAll(".nav-item")
        .forEach(item => {

            item.classList.toggle(
                "active",
                item.dataset.view === view
            );

        });

}


/* =========================================================
   SEARCH
========================================================= */

function setupSearch() {

    searchInput.addEventListener(
        "input",
        () => {

            const query =
                searchInput.value
                    .toLowerCase()
                    .trim();


            if (!query) {

                renderDashboard();

                return;

            }


            const results =
                projects.filter(
                    project => {

                        const searchable =
                            [
                                project.title,
                                project.description,
                                project.category,
                                project.status,
                                ...project.technologies
                            ]
                                .join(" ")
                                .toLowerCase();

                        return searchable.includes(
                            query
                        );

                    }
                );


            projectGrid.innerHTML = "";

            results.forEach(
                project => {

                    projectGrid.appendChild(
                        createProjectCard(project)
                    );

                }
            );

        }
    );

}


/* =========================================================
   FILTERS
========================================================= */

function setupFilters() {

    document
        .querySelectorAll(".filter")
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    document
                        .querySelectorAll(
                            ".filter"
                        )
                        .forEach(
                            b =>
                            b.classList.remove(
                                "active"
                            )
                        );


                    button.classList.add(
                        "active"
                    );


                    currentStatus =
                        button.dataset.status;


                    renderAllProjects();

                }
            );

        });


    document
        .querySelectorAll(
            ".category-button"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    const category =
                        button.dataset.category;


                    const results =
                        projects.filter(
                            project =>
                                project.category ===
                                category
                        );


                    switchView("projects");


                    allProjectGrid.innerHTML =
                        "";


                    results.forEach(
                        project => {

                            allProjectGrid.appendChild(
                                createProjectCard(
                                    project
                                )
                            );

                        }
                    );

                }
            );

        });

}


/* =========================================================
   MODALS
========================================================= */

function setupModals() {

    document
        .getElementById("modalClose")
        .addEventListener(
            "click",
            closeProjectModal
        );


    projectModal.addEventListener(
        "click",
        event => {

            if (
                event.target ===
                projectModal
            ) {

                closeProjectModal();

            }

        }
    );


    document
        .getElementById("addProjectButton")
        .addEventListener(
            "click",
            () => {

                addModal.classList.add(
                    "visible"
                );

            }
        );


    document
        .getElementById("addModalClose")
        .addEventListener(
            "click",
            () => {

                addModal.classList.remove(
                    "visible"
                );

            }
        );


    document
        .getElementById("projectForm")
        .addEventListener(
            "submit",
            handleNewProject
        );

}


function closeProjectModal() {

    projectModal.classList.remove(
        "visible"
    );

}


/* =========================================================
   ADD PROJECT
========================================================= */

function handleNewProject(event) {

    event.preventDefault();


    const name =
        document
            .getElementById("projectName")
            .value
            .trim();


    const description =
        document
            .getElementById(
                "projectDescription"
            )
            .value
            .trim();


    const category =
        document
            .getElementById(
                "projectCategory"
            )
            .value;


    const status =
        document
            .getElementById(
                "projectStatus"
            )
            .value;


    const tech =
        document
            .getElementById(
                "projectTech"
            )
            .value
            .split(",")
            .map(t => t.trim())
            .filter(Boolean);


    const newProject = {

        id:
            name
                .toLowerCase()
                .replace(
                    /[^a-z0-9]+/g,
                    "-"
                ),

        title: name,

        category,

        status,

        description,

        technologies: tech,

        icon: "◇",

        favorite: false,

        details: {

            problem:
                "Problem statement to be researched.",

            solution:
                "Proposed solution.",

            architecture:
                [
                    "Architecture to be designed."
                ],

            features:
                [
                    "Feature ideas."
                ],

            example:
                "Example command or workflow.",

            questions:
                [
                    "Questions for the team."
                ]

        }

    };


    projects.unshift(
        newProject
    );


    updateStats();

    renderDashboard();

    renderAllProjects();

    renderFavorites();


    event.target.reset();

    addModal.classList.remove(
        "visible"
    );


    switchView("projects");

}


/* =========================================================
   KEYBOARD SHORTCUTS
========================================================= */

function setupKeyboardShortcuts() {

    document.addEventListener(
        "keydown",
        event => {

            if (
                (event.ctrlKey ||
                 event.metaKey) &&
                event.key.toLowerCase() === "k"
            ) {

                event.preventDefault();

                searchInput.focus();

            }


            if (
                event.key === "Escape"
            ) {

                closeProjectModal();

                addModal.classList.remove(
                    "visible"
                );

            }

        }
    );

}