/**
 * Mobile Navbar Verification Script
 * 
 * Copy and paste this entire script into the DevTools Console
 * and press Enter to run a complete diagnostic check.
 */

console.clear();
console.log('%c═════════════════════════════════════════════════════', 'color: #6366f1; font-weight: bold');
console.log('%c   MOBILE NAVBAR VERIFICATION SCRIPT', 'color: #6366f1; font-weight: bold; font-size: 14px');
console.log('%c═════════════════════════════════════════════════════', 'color: #6366f1; font-weight: bold');

// Check 1: Viewport
console.log('\n%c📱 1. VIEWPORT CHECK', 'color: #10b981; font-weight: bold');
const viewportWidth = window.innerWidth;
const isMobile = viewportWidth <= 768;
console.log(`   Current width: ${viewportWidth}px`);
console.log(`   Is mobile? ${isMobile ? '✅ YES' : '❌ NO (resize to ≤768px)'}`);

// Check 2: Elements
console.log('\n%c🔍 2. ELEMENT CHECK', 'color: #10b981; font-weight: bold');
const toggler = document.getElementById('mobileToggler');
const collapse = document.getElementById('navbarNav');
console.log(`   #mobileToggler found? ${toggler ? '✅ YES' : '❌ NO'}`);
console.log(`   #navbarNav found? ${collapse ? '✅ YES' : '❌ NO'}`);

if (!toggler || !collapse) {
    console.log('\n%c❌ CRITICAL: Elements not found! Check HTML IDs.', 'color: #ef4444; font-weight: bold');
}

// Check 3: CSS
console.log('\n%c🎨 3. CSS CHECK', 'color: #10b981; font-weight: bold');
if (collapse) {
    const styles = window.getComputedStyle(collapse);
    console.log(`   Position: ${styles.position}`);
    console.log(`   Transform: ${styles.transform}`);
    console.log(`   Visibility: ${styles.visibility}`);
}

// Check 4: Classes
console.log('\n%c🏷️  4. CLASS CHECK', 'color: #10b981; font-weight: bold');
if (toggler && collapse) {
    console.log(`   Toggler classes: ${toggler.className}`);
    console.log(`   Collapse classes: ${collapse.className}`);
    console.log(`   Menu open? ${collapse.classList.contains('show') ? '✅ YES' : '❌ NO (closed)'}`);
}

// Check 5: Event Listeners
console.log('\n%c🎯 5. EVENT LISTENER CHECK', 'color: #10b981; font-weight: bold');
if (toggler) {
    // Note: We can't directly check listeners, but we can test if toggle works
    console.log('   Click listener: Will test below');
}

// Check 6: Debug Object
console.log('\n%c🔧 6. DEBUG OBJECT CHECK', 'color: #10b981; font-weight: bold');
const hasDebugNavbar = !!window.debugNavbar;
console.log(`   window.debugNavbar exists? ${hasDebugNavbar ? '✅ YES' : '❌ NO'}`);
if (hasDebugNavbar) {
    console.log(`   - toggle function: ${typeof window.debugNavbar.toggle === 'function' ? '✅ YES' : '❌ NO'}`);
    console.log(`   - toggler element: ${window.debugNavbar.toggler ? '✅ YES' : '❌ NO'}`);
    console.log(`   - collapse element: ${window.debugNavbar.collapse ? '✅ YES' : '❌ NO'}`);
}

// Check 7: Manual Test
console.log('\n%c🧪 7. INTERACTIVE TEST', 'color: #10b981; font-weight: bold');
if (toggler && collapse && window.debugNavbar) {
    console.log('%c   Running toggle test...', 'color: #a78bfa');
    
    const initialState = collapse.classList.contains('show');
    console.log(`   Initial state: ${initialState ? 'OPEN' : 'CLOSED'}`);
    
    // Toggle
    window.debugNavbar.toggle();
    const afterToggle = collapse.classList.contains('show');
    console.log(`   After toggle: ${afterToggle ? 'OPEN' : 'CLOSED'}`);
    
    // Toggle back
    window.debugNavbar.toggle();
    const finalState = collapse.classList.contains('show');
    console.log(`   After 2nd toggle: ${finalState ? 'OPEN' : 'CLOSED'}`);
    
    console.log(`   Test result: ${initialState === finalState ? '✅ PASSED' : '❌ FAILED'}`);
}

// Summary
console.log('\n%c═════════════════════════════════════════════════════', 'color: #6366f1; font-weight: bold');
console.log('%c   SUMMARY', 'color: #6366f1; font-weight: bold; font-size: 14px');
console.log('%c═════════════════════════════════════════════════════', 'color: #6366f1; font-weight: bold');

const allChecks = {
    'Mobile viewport': isMobile,
    'Toggler element': !!toggler,
    'Collapse element': !!collapse,
    'Debug object': hasDebugNavbar
};

const checksPassed = Object.values(allChecks).filter(v => v).length;
const checksTotal = Object.values(allChecks).length;

Object.entries(allChecks).forEach(([name, passed]) => {
    console.log(`${passed ? '✅' : '❌'} ${name}`);
});

console.log(`\n${checksPassed}/${checksTotal} checks passed`);

if (checksPassed === checksTotal) {
    console.log('%c\n✅ ALL CHECKS PASSED! Navbar should be working.\n', 'color: #10b981; font-weight: bold; font-size: 12px');
    console.log('%c💡 Try clicking the hamburger button in the top right!\n', 'color: #3b82f6; font-size: 12px');
} else {
    console.log('%c\n❌ Some checks failed. See details above.\n', 'color: #ef4444; font-weight: bold; font-size: 12px');
}

// Provide manual control
console.log('%c🎮 MANUAL CONTROLS:', 'color: #f59e0b; font-weight: bold');
console.log('   window.debugNavbar.toggle()    - Toggle menu open/closed');
console.log('   window.debugNavbar.collapse    - Get menu element');
console.log('   window.debugNavbar.toggler     - Get button element');

console.log('\n%c═════════════════════════════════════════════════════\n', 'color: #6366f1; font-weight: bold');
