import { useApp } from '../state/store';

export function SaudiMap({ onSelect }: { onSelect: (region: string) => void }) {
  const { theme } = useApp();
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || theme === 'dark';

  // يمكنك تحديد الإقليم الافتراضي أو التعامل مع النقرات حسب الحاجة
  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // كمثال تجريبي لتفعيل الحدث عند الضغط، أو يمكنك تخصيصه حسب مساحات الأقاليم
    // إذا كنتِ ترغبين بتمرير إقليم معين عند النقر المباشر:
    onSelect('Central'); // أو المنطقة المستهدفة
  };

  return (
    <div 
      className="saudi-map-wrapper" 
      style={{ cursor: 'pointer', position: 'relative' }}
      onClick={handleClick}
    >
      <img 
        src={isDark ? '/map-dark.png' : '/map-light.png'} 
        alt="Saudi Arabia Map" 
        style={{ 
          width: '100%', 
          height: 'auto', 
          objectFit: 'contain',
          display: 'block' 
        }} 
      />
    </div>
  );
}