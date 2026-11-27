import { Link } from 'react-router-dom';
import { Text } from '@/components/atoms';

export function NotFoundPage() {
  return (
    <section>
      <Text as="h2" size="xl" bold>
        페이지를 찾을 수 없습니다
      </Text>
      <Text as="p" muted>
        <Link to="/">대시보드로 돌아가기</Link>
      </Text>
    </section>
  );
}
