import React, { useEffect, useState } from 'react'
import { GITHUB_REPO } from '../utils/links'
import './Contributors.css'

export default function Contributors() {
    const [contributors, setContributors] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let repoPath = ''
        try {
            // Robust URL parsing to handle potential trailing slashes or different formats
            const urlObj = new URL(GITHUB_REPO)
            // Example: /SkriptyRobert/Parential-Control_Enterprise
            const parts = urlObj.pathname.split('/').filter(Boolean)
            if (parts.length >= 2) {
                repoPath = `${parts[0]}/${parts[1]}`
            } else {
                throw new Error('Invalid GitHub URL structure')
            }
        } catch (e) {
            console.warn('Contributors: URL parsing failed', e)
            setLoading(false)
            return
        }

        const api = `https://api.github.com/repos/${repoPath}/contributors`

        fetch(api)
            .then((res) => {
                if (!res.ok) {
                    // 404/403 often means private repo or incorrect name
                    throw new Error(`API returned ${res.status}`)
                }
                return res.json()
            })
            .then((data) => {
                if (!Array.isArray(data)) throw new Error('Invalid data format')

                const excludeLogins = [
                    'cursoragent', 'cursor-agent', 'cursor_agent', 'cursor',
                    'github-actions[bot]', 'dependabot[bot]', 'renovate[bot]'
                ]
                const isExcluded = (u) => {
                    const login = (u.login || '').toLowerCase()
                    if (excludeLogins.some(ex => login.includes(ex) || ex.includes(login))) return true
                    const name = (u.login || '') + (u.name || '')
                    if (/cursor\s*agent|agent\s*cursor/i.test(name)) return true
                    return false
                }
                const users = data
                    .filter(u => u.type === 'User' && !isExcluded(u))
                    .slice(0, 30)
                // Duplicate list for seamless infinite scroll
                setContributors([...users, ...users])
                setLoading(false)
            })
            .catch((err) => {
                console.warn('Contributors: Failed to load from API (Repo might be private). Using fallback.', err)

                // MANUAL FALLBACK: Use this when API fails (e.g. private repo)
                // This ensures the section is always visible
                const manualContributors = [
                    {
                        id: 'owner-1',
                        html_url: 'https://github.com/SkriptyRobert',
                        login: 'SkriptyRobert',
                        avatar_url: 'https://github.com/SkriptyRobert.png',
                        contributions: 'Owner'
                    },
                    // Add more contributors manually here if needed
                ]

                setContributors([...manualContributors, ...manualContributors])
                setLoading(false)
            })
    }, [])

    if (loading || contributors.length === 0) return null

    return (
        <section className="contributors">
            <div className="contributors-inner">
                <h3 className="contributors-label">Kdo přispěl kódem:</h3>
                <div className="contributors-marquee">
                    <div className="contributors-track">
                        {contributors.map((user, index) => (
                            <a
                                key={`${user.id}-${index}`}
                                href={user.html_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="contributor-item"
                                title={`${user.login}`}
                            >
                                <img
                                    src={user.avatar_url}
                                    alt={user.login}
                                    className="contributor-avatar"
                                    loading="lazy"
                                />
                            </a>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    )
}
